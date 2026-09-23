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

from unittest import mock

from neutron.conf.plugins.ml2.drivers.ovn import ovn_conf
from neutron.tests import base
from neutron_lib.callbacks import events
from neutron_lib.callbacks import resources

from neutron_taas.services.taas.service_drivers.ovn import helper


class TestTaasOvnProviderHelper(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        ovn_conf.register_opts()

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

        mock.patch(
            'ovsdbapp.backend.ovs_idl.idlutils.get_schema_helper').start()
        self.helper = helper.TaasOvnProviderHelper()
        self.helper._post_fork_initialize(
            resources.PROCESS, events.AFTER_INIT, None)

        self.ovn_nbdb_api = mock.patch.object(self.helper, 'ovn_nbdb_api')
        self.ovn_nbdb_api.start()
        self.addCleanup(self.ovn_nbdb_api.stop)

        add_req_thread = mock.patch.object(helper.TaasOvnProviderHelper,
                                           'add_request')
        self.mock_add_request = add_req_thread.start()
        self.addCleanup(add_req_thread.stop)

    def test_mirror_add(self):
        port_id = '1234'
        name = 'foo_mirror'
        dest_ip = '10.92.10.5'
        type = 'gre'
        tunnel_id = 101
        direction = 'to-lport'

        self.helper.mirror_add({
            'name': name,
            'direction_filter': direction,
            'dest': dest_ip,
            'mirror_type': type,
            'index': tunnel_id,
            'port_id': port_id
        })

        self.helper.ovn_nbdb_api.lookup.assert_called_once_with(
            'Logical_Switch_Port', port_id)
        self.helper.ovn_nbdb_api.mirror_add.assert_called_once_with(
            name=name,
            direction_filter=direction,
            dest=dest_ip,
            mirror_type=type,
            index=tunnel_id
        )
        self.helper.ovn_nbdb_api.lsp_attach_mirror.assert_called_once()

    def test_mirror_del(self):
        port_id = '1234'
        name = 'foo_mirror'
        dest_ip = '10.92.10.5'
        type = 'gre'
        tunnel_id = 101
        direction = 'to-lport'

        self.helper.mirror_del({
            'port_id': port_id,
            'name': name,
            'direction_filter': direction,
            'dest': dest_ip,
            'mirror_type': type,
            'index': tunnel_id,
            'port_id': port_id
        })

        self.helper.ovn_nbdb_api.lookup.assert_called_once_with(
            'Logical_Switch_Port', port_id)
        self.helper.ovn_nbdb_api.mirror_get.assert_called_once_with(name)
        self.helper.ovn_nbdb_api.lsp_detach_mirror.assert_called_once()
        self.helper.ovn_nbdb_api.mirror_del.assert_called_once()

    def test_mirror_add_lport(self):
        port_id = '1234'
        remote_port_id = '5678'
        self.helper.mirror_add({
            'name': 'tm_abcdef',
            'direction_filter': 'both',
            'dest': remote_port_id,
            'mirror_type': 'lport',
            'index': 0,
            'port_id': port_id
        })
        self.helper.ovn_nbdb_api.lookup.assert_called_once_with(
            'Logical_Switch_Port', port_id)
        self.helper.ovn_nbdb_api.mirror_add.assert_called_once_with(
            name='tm_abcdef', direction_filter='both', dest=remote_port_id,
            mirror_type='lport', index=0)
        self.helper.ovn_nbdb_api.lsp_attach_mirror.assert_called_once()

    def test_mirror_rule_add(self):
        mirror = self.helper.ovn_nbdb_api.mirror_get.return_value.execute(
            check_error=True)
        self.helper.mirror_rule_add({
            'name': 'tm_abcdef', 'priority': 100,
            'match': 'ip4 && tcp && tcp.dst == 443', 'action': 'mirror'})
        self.helper.ovn_nbdb_api.mirror_get.assert_called_with('tm_abcdef')
        self.helper.ovn_nbdb_api.mirror_rule_add.assert_called_once_with(
            mirror.uuid, 100, 'ip4 && tcp && tcp.dst == 443', 'mirror',
            may_exist=True)

    def test_mirror_rule_del(self):
        mirror = self.helper.ovn_nbdb_api.mirror_get.return_value.execute(
            check_error=True)
        self.helper.mirror_rule_del({
            'name': 'tm_abcdef', 'priority': 0, 'match': '1'})
        self.helper.ovn_nbdb_api.mirror_get.assert_called_with('tm_abcdef')
        self.helper.ovn_nbdb_api.mirror_rule_del.assert_called_once_with(
            mirror.uuid, priority=0, match='1', if_exists=True)
