# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from neutron_lib.api.definitions import taas as taas_api_def
from neutron_lib.api.definitions import tap_mirror as tap_m_api_def
from neutron_lib.api.definitions import tap_mirror_lport as tap_m_l_api_def
from neutron_lib.api.definitions import tap_mirror_rules as tap_m_r_api_def
from oslo_log import helpers as log_helpers
from oslo_log import log as logging

from neutron_taas.common import utils as taas_utils
from neutron_taas.services.taas import service_drivers
from neutron_taas.services.taas.service_drivers.ovn import helper
from neutron_taas.services.taas.service_drivers.ovn import match


LOG = logging.getLogger(__name__)


class TaasOvnDriver(service_drivers.TaasBaseDriver):
    """Taas OVN Service Driver class"""

    driver_name = "TaaS OVN Driver"
    more_supported_extension_aliases = [tap_m_api_def.ALIAS,
                                        tap_m_l_api_def.ALIAS,
                                        tap_m_r_api_def.ALIAS]

    def __init__(self, service_plugin):
        LOG.debug("Loading Taas OVN Driver.")
        super().__init__(service_plugin)
        self._ovn_helper = helper.TaasOvnProviderHelper()

    def __del__(self):
        self._ovn_helper.shutdown()

    @log_helpers.log_method_call
    def create_tap_service_precommit(self, context):
        raise NotImplementedError(
            f"Create tap service is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def create_tap_service_postcommit(self, context):
        raise NotImplementedError(
            f"Create tap service is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def delete_tap_service_precommit(self, context):
        raise NotImplementedError(
            f"Delete tap service is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def delete_tap_service_postcommit(self, context):
        raise NotImplementedError(
            f"Delete tap service is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def create_tap_flow_precommit(self, context):
        raise NotImplementedError(
            f"Create tap flow is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def create_tap_flow_postcommit(self, context):
        raise NotImplementedError(
            f"Create tap flow is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def delete_tap_flow_precommit(self, context):
        raise NotImplementedError(
            f"Delete tap flow is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def delete_tap_flow_postcommit(self, context):
        raise NotImplementedError(
            f"Delete tap flow is not supported by {self.driver_name}.")

    @log_helpers.log_method_call
    def create_tap_mirror_precommit(self, context):
        pass

    @staticmethod
    def _is_lport(t_m):
        return t_m['mirror_type'] == tap_m_l_api_def.MIRROR_TYPE_LPORT

    # OVN mirror filter per Tap Mirror direction.
    _LPORT_FILTERS = {taas_api_def.DIRECTION_IN: 'to-lport',
                      taas_api_def.DIRECTION_OUT: 'from-lport'}

    @staticmethod
    def _lport_mirror_name(t_m, direction):
        # One OVN Mirror per mirrored direction, like gre/erspan mirrors, so
        # that rules can be restricted to a direction.
        return 'tm_%s_%s' % (direction.lower(), t_m['id'][0:6])

    def _lport_mirrors(self, t_m, direction=None):
        """Yield (direction, OVN mirror name) for a Tap Mirror.

        ``direction`` restricts the result to that direction when given.
        """
        for d in taas_utils.expand_directions(t_m['directions']):
            if direction is None or d == direction:
                yield d, self._lport_mirror_name(t_m, d)

    def _create_lport_mirror(self, t_m):
        for direction, name in self._lport_mirrors(t_m):
            request = {'type': 'mirror_add',
                       'info': {'name': name,
                                'direction_filter':
                                    self._LPORT_FILTERS[direction],
                                'dest': t_m[tap_m_l_api_def.REMOTE_PORT_ID],
                                'mirror_type':
                                    tap_m_l_api_def.MIRROR_TYPE_LPORT,
                                'index': 0,
                                'port_id': t_m['port_id']}}
            self._ovn_helper.add_request(request)

    def _delete_lport_mirror(self, t_m):
        for _direction, name in self._lport_mirrors(t_m):
            request = {'type': 'mirror_del',
                       'info': {'id': t_m['id'],
                                'name': name,
                                'sink': t_m[tap_m_l_api_def.REMOTE_PORT_ID],
                                'port_id': t_m['port_id']}}
            self._ovn_helper.add_request(request)

    @log_helpers.log_method_call
    def create_tap_mirror_postcommit(self, context):
        LOG.info('create_tap_mirror_postcommit %s', context.tap_mirror)
        t_m = context.tap_mirror
        if self._is_lport(t_m):
            self._create_lport_mirror(t_m)
            return
        type = 'erspan' if 'erspan' in t_m['mirror_type'] else 'gre'
        directions = t_m['directions']
        for direction, tunnel_id in directions.items():
            mirror_port_name = 'tm_%s_%s' % (direction.lower(), t_m['id'][0:6])
            ovn_direction = ('from-lport' if direction == 'OUT'
                             else 'to-lport' if direction == 'IN'
                             else 'both')
            request = {'type': 'mirror_add',
                       'info': {'name': mirror_port_name,
                                'direction_filter': ovn_direction,
                                'dest': t_m['remote_ip'],
                                'mirror_type': type,
                                'index': int(tunnel_id),
                                'port_id': t_m['port_id']}}
            self._ovn_helper.add_request(request)

    @log_helpers.log_method_call
    def delete_tap_mirror_precommit(self, context):
        LOG.info('delete_tap_mirror_precommit %s', context.tap_mirror)
        t_m = context.tap_mirror
        if self._is_lport(t_m):
            self._delete_lport_mirror(t_m)
            return
        directions = t_m['directions']
        for direction, tunnel_id in directions.items():
            mirror_port_name = 'tm_%s_%s' % (direction.lower(), t_m['id'][0:6])
            request = {
                'type': 'mirror_del',
                'info': {'id': t_m['id'],
                         'name': mirror_port_name,
                         'sink': t_m['remote_ip'],
                         'port_id': t_m['port_id']}
            }
            self._ovn_helper.add_request(request)

    @log_helpers.log_method_call
    def delete_tap_mirror_postcommit(self, context):
        pass

    @log_helpers.log_method_call
    def create_tap_mirror_rule_postcommit(self, context):
        rule = context.rule
        ovn_match = match.rule_to_ovn_match(rule)
        for _direction, name in self._lport_mirrors(context.tap_mirror,
                                                    rule.get('direction')):
            request = {'type': 'mirror_rule_add',
                       'info': {'name': name,
                                'priority': rule['priority'],
                                'match': ovn_match,
                                'action': rule['action']}}
            self._ovn_helper.add_request(request)

    @log_helpers.log_method_call
    def delete_tap_mirror_rule_precommit(self, context):
        rule = context.rule
        ovn_match = match.rule_to_ovn_match(rule)
        for _direction, name in self._lport_mirrors(context.tap_mirror,
                                                    rule.get('direction')):
            request = {'type': 'mirror_rule_del',
                       'info': {'name': name,
                                'priority': rule['priority'],
                                'match': ovn_match}}
            self._ovn_helper.add_request(request)
