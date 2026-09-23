#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
from unittest import mock

from neutron.tests import base
from oslo_utils import uuidutils

from neutron_taas.services.taas.service_drivers.ovn import helper
from neutron_taas.services.taas.service_drivers.ovn import taas_ovn


class FakeMirrorContext():
    def __init__(self, tap_mirror, rule=None):
        self._tap_mirror = tap_mirror
        self._rule = rule

    @property
    def tap_mirror(self):
        return self._tap_mirror

    @property
    def rule(self):
        return self._rule


class TestTaasOvnDriver(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        ovn_nb_idl = mock.patch(
            'neutron_taas.services.taas.service_drivers.ovn.ovsdb.'
            'impl_idl_taas.OvnNbIdlForTaas')
        self.mock_ovn_nb_idl = ovn_nb_idl.start()
        self.addCleanup(ovn_nb_idl.stop)

        mock_thread = mock.patch(
            'neutron_taas.services.taas.service_drivers.ovn.helper.'
            'threading.Thread')
        self.mock_thread_class = mock_thread.start()
        self.addCleanup(mock_thread.stop)

        self.driver = taas_ovn.TaasOvnDriver('tapmirror')

        add_req_thread = mock.patch.object(helper.TaasOvnProviderHelper,
                                           'add_request')
        self.mock_add_request = add_req_thread.start()
        self.addCleanup(add_req_thread.stop)

        self.tap_mirror_dict = {
            'mirror_type': 'gre',
            'directions': {'IN': 101},
            'id': uuidutils.generate_uuid(),
            'remote_ip': '10.92.10.5',
            'port_id': uuidutils.generate_uuid()
        }
        self.multi_dir_t_mirror = copy.deepcopy(self.tap_mirror_dict)
        self.multi_dir_t_mirror['directions'] = {'IN': 101,
                                                 'OUT': 102,
                                                 'BOTH': 103}
        self.lport_t_mirror = {
            'mirror_type': 'lport',
            'directions': {'BOTH': None},
            'id': uuidutils.generate_uuid(),
            'remote_ip': None,
            'remote_port_id': uuidutils.generate_uuid(),
            'port_id': uuidutils.generate_uuid()
        }
        self.lport_rule = {
            'id': uuidutils.generate_uuid(),
            'priority': 100,
            'action': 'mirror',
            'ethertype': 'IPv4',
            'protocol': 'tcp',
            'source_ip_prefix': None,
            'destination_ip_prefix': None,
            'source_port_range_min': None,
            'source_port_range_max': None,
            'destination_port_range_min': 443,
            'destination_port_range_max': 443,
        }

    def test_create_tap_mirror_postcommit(self):
        ctx = FakeMirrorContext(self.tap_mirror_dict)
        self.driver.create_tap_mirror_postcommit(ctx)
        expected_dict = {
            'type': 'mirror_add',
            'info': {
                'name': mock.ANY,
                'direction_filter': 'to-lport',
                'dest': self.tap_mirror_dict['remote_ip'],
                'mirror_type': self.tap_mirror_dict['mirror_type'],
                'index': self.tap_mirror_dict['directions']['IN'],
                'port_id': self.tap_mirror_dict['port_id'],
            }
        }
        self.mock_add_request.assert_called_once_with(expected_dict)

    def test_create_tap_mirror_postcommit_multi_dir(self):
        ctx = FakeMirrorContext(self.multi_dir_t_mirror)
        self.driver.create_tap_mirror_postcommit(ctx)

        expected_in_call = {
            'type': 'mirror_add',
            'info': {
                'name': mock.ANY,
                'direction_filter': 'to-lport',
                'dest': self.tap_mirror_dict['remote_ip'],
                'mirror_type': self.tap_mirror_dict['mirror_type'],
                'index': self.tap_mirror_dict['directions']['IN'],
                'port_id': self.tap_mirror_dict['port_id'],
            }
        }
        expected_out_call = copy.deepcopy(expected_in_call)
        expected_out_call['info']['direction_filter'] = 'from-lport'
        out_dir_tun_id = self.multi_dir_t_mirror['directions']['OUT']
        expected_out_call['info']['index'] = out_dir_tun_id

        expected_both_call = copy.deepcopy(expected_in_call)
        expected_both_call['info']['direction_filter'] = 'both'
        both_dir_tun_id = self.multi_dir_t_mirror['directions']['BOTH']
        expected_both_call['info']['index'] = both_dir_tun_id
        expected_calls = [
            mock.call(expected_in_call),
            mock.call(expected_out_call),
            mock.call(expected_both_call)
        ]

        self.mock_add_request.assert_has_calls(expected_calls)

    def test_delete_tap_mirror_precommit(self):
        ctx = FakeMirrorContext(self.tap_mirror_dict)
        self.driver.delete_tap_mirror_precommit(ctx)

        expected_dict = {
            'type': 'mirror_del',
            'info': {
                'id': self.tap_mirror_dict['id'],
                'name': mock.ANY,
                'sink': self.tap_mirror_dict['remote_ip'],
                'port_id': self.tap_mirror_dict['port_id']}
        }
        self.mock_add_request.assert_called_once_with(expected_dict)

    def test_delete_tap_mirror_precommit_multi_dir(self):
        ctx = FakeMirrorContext(self.multi_dir_t_mirror)
        self.driver.delete_tap_mirror_precommit(ctx)

        expected_call = {
            'type': 'mirror_del',
            'info': {
                'id': self.tap_mirror_dict['id'],
                'name': mock.ANY,
                'sink': self.tap_mirror_dict['remote_ip'],
                'port_id': self.tap_mirror_dict['port_id'],
            }
        }

        expected_calls = [
            mock.call(expected_call),
            mock.call(expected_call)
        ]

        self.mock_add_request.assert_has_calls(expected_calls)

    def _lport_names(self, t_m=None):
        t_m = t_m or self.lport_t_mirror
        return ('tm_in_%s' % t_m['id'][0:6], 'tm_out_%s' % t_m['id'][0:6])

    def test_create_lport_tap_mirror_postcommit(self):
        ctx = FakeMirrorContext(self.lport_t_mirror)
        self.driver.create_tap_mirror_postcommit(ctx)
        name_in, name_out = self._lport_names()
        expected_in = {
            'type': 'mirror_add',
            'info': {
                'name': name_in,
                'direction_filter': 'to-lport',
                'dest': self.lport_t_mirror['remote_port_id'],
                'mirror_type': 'lport',
                'index': 0,
                'port_id': self.lport_t_mirror['port_id'],
            }
        }
        expected_out = copy.deepcopy(expected_in)
        expected_out['info'].update({'name': name_out,
                                     'direction_filter': 'from-lport'})
        # BOTH is expanded into one OVN mirror per direction.
        self.mock_add_request.assert_has_calls(
            [mock.call(expected_in), mock.call(expected_out)])
        self.assertEqual(2, self.mock_add_request.call_count)

    def test_create_lport_tap_mirror_postcommit_single_direction(self):
        name_in, name_out = self._lport_names()
        for directions, expected in (
                ({'IN': None}, [(name_in, 'to-lport')]),
                ({'OUT': None}, [(name_out, 'from-lport')]),
                ({'IN': None, 'OUT': None}, [(name_in, 'to-lport'),
                                             (name_out, 'from-lport')])):
            self.mock_add_request.reset_mock()
            t_m = dict(self.lport_t_mirror, directions=directions)
            self.driver.create_tap_mirror_postcommit(FakeMirrorContext(t_m))
            got = [(c[0][0]['info']['name'],
                    c[0][0]['info']['direction_filter'])
                   for c in self.mock_add_request.call_args_list]
            self.assertEqual(expected, got)

    def test_delete_lport_tap_mirror_precommit(self):
        ctx = FakeMirrorContext(self.lport_t_mirror)
        self.driver.delete_tap_mirror_precommit(ctx)
        expected = []
        for name in self._lport_names():
            expected.append(mock.call({
                'type': 'mirror_del',
                'info': {
                    'id': self.lport_t_mirror['id'],
                    'name': name,
                    'sink': self.lport_t_mirror['remote_port_id'],
                    'port_id': self.lport_t_mirror['port_id']}}))
        self.mock_add_request.assert_has_calls(expected)
        self.assertEqual(2, self.mock_add_request.call_count)

    def test_create_tap_mirror_rule_postcommit(self):
        ctx = FakeMirrorContext(self.lport_t_mirror, self.lport_rule)
        self.driver.create_tap_mirror_rule_postcommit(ctx)
        expected = []
        for name in self._lport_names():
            expected.append(mock.call({
                'type': 'mirror_rule_add',
                'info': {
                    'name': name,
                    'priority': 100,
                    'match': 'ip4 && tcp && tcp.dst == 443',
                    'action': 'mirror'}}))
        # A rule without direction goes to every mirror of the Tap Mirror.
        self.mock_add_request.assert_has_calls(expected)
        self.assertEqual(2, self.mock_add_request.call_count)

    def test_create_tap_mirror_rule_postcommit_with_direction(self):
        rule = dict(self.lport_rule, direction='IN')
        ctx = FakeMirrorContext(self.lport_t_mirror, rule)
        self.driver.create_tap_mirror_rule_postcommit(ctx)
        name_in, _name_out = self._lport_names()
        self.mock_add_request.assert_called_once()
        self.assertEqual(name_in,
                         self.mock_add_request.call_args[0][0]['info']['name'])

    def test_delete_tap_mirror_rule_precommit(self):
        rule = dict(self.lport_rule, direction='OUT')
        ctx = FakeMirrorContext(self.lport_t_mirror, rule)
        self.driver.delete_tap_mirror_rule_precommit(ctx)
        _name_in, name_out = self._lport_names()
        expected_dict = {
            'type': 'mirror_rule_del',
            'info': {
                'name': name_out,
                'priority': 100,
                'match': 'ip4 && tcp && tcp.dst == 443'}
        }
        self.mock_add_request.assert_called_once_with(expected_dict)
