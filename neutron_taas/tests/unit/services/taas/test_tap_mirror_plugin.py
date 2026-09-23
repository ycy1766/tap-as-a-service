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

import contextlib

import testtools
from unittest import mock

from neutron.tests.unit import testlib_api
from neutron_lib import context
from neutron_lib.exceptions import taas as taas_exc
from neutron_lib import rpc as n_rpc
from neutron_lib.utils import net as n_utils
from oslo_utils import uuidutils

from neutron_taas.services.taas import tap_mirror_plugin


class TestTapMirrorPlugin(testlib_api.SqlTestCase):
    def setUp(self):
        super().setUp()
        mock.patch.object(n_rpc, 'Connection', spec=object).start()

        self.driver = mock.MagicMock()
        mock.patch('neutron.services.service_base.load_drivers',
                   return_value=({'dummy_provider': self.driver},
                                 'dummy_provider')).start()
        mock.patch('neutron.db.servicetype_db.ServiceTypeManager.get_instance',
                   return_value=mock.MagicMock()).start()
        self._plugin = tap_mirror_plugin.TapMirrorPlugin()
        self._context = context.get_admin_context()

        self._project_id = self._tenant_id = uuidutils.generate_uuid()
        self._network_id = uuidutils.generate_uuid()
        self._host_id = 'host-A'
        self._port_id = uuidutils.generate_uuid()
        self._port_details = {
            'tenant_id': self._tenant_id,
            'binding:host_id': self._host_id,
            'mac_address': n_utils.get_random_mac(
                'fa:16:3e:00:00:00'.split(':')),
        }
        self._tap_mirror = {
            'project_id': self._project_id,
            'tenant_id': self._tenant_id,
            'name': 'MyMirror',
            'description': 'This is my Tap Mirror',
            'port_id': self._port_id,
            'directions': {"IN": 101},
            'remote_ip': '10.99.8.3',
            'remote_port_id': None,
            'mirror_type': 'gre',
        }
        self._remote_port_id = uuidutils.generate_uuid()
        self._lport_kwargs = {
            'mirror_type': 'lport',
            'remote_ip': None,
            'remote_port_id': self._remote_port_id,
            'directions': {'BOTH': None},
        }

    @contextlib.contextmanager
    def tap_mirror(self, **kwargs):
        self._tap_mirror.update(kwargs)
        req = {
            'tap_mirror': self._tap_mirror,
        }
        with mock.patch.object(self._plugin, 'get_port_details',
                               return_value=self._port_details):
            mirror = self._plugin.create_tap_mirror(self._context, req)
        self._tap_mirror['id'] = mock.ANY

        self.driver.assert_has_calls([
            mock.call.create_tap_mirror_precommit(mock.ANY),
            mock.call.create_tap_mirror_postcommit(mock.ANY),
        ])
        pre_call_args = self.driver.create_tap_mirror_precommit.call_args[0][0]
        self.assertEqual(self._context, pre_call_args._plugin_context)
        self.assertEqual(self._tap_mirror, pre_call_args.tap_mirror)

        post_call_args = self.driver.create_tap_mirror_postcommit.call_args
        post_call_args = post_call_args[0][0]
        self.assertEqual(self._context, post_call_args._plugin_context)
        self.assertEqual(self._tap_mirror, post_call_args.tap_mirror)

        yield self._plugin.get_tap_mirror(self._context,
                                          mirror['id'])

    def test_create_tap_mirror(self):
        with self.tap_mirror():
            pass

    def test_create_tap_mirror_wrong_project_id(self):
        self._port_details['project_id'] = 'other-tenant'
        self._port_details['tenant_id'] = 'other-tenant'
        with testtools.ExpectedException(taas_exc.PortDoesNotBelongToTenant), \
                self.tap_mirror():
            pass
        self.assertEqual([], self.driver.mock_calls)

    def test_create_duplicate_tunnel_id(self):
        with self.tap_mirror() as tm1:
            with mock.patch.object(self._plugin, 'get_tap_mirrors',
                                   return_value=[tm1]):
                with testtools.ExpectedException(
                        taas_exc.TapMirrorTunnelConflict), \
                        self.tap_mirror(directions={"IN": 101}):
                    pass

    def test_create_different_tunnel_id(self):
        with self.tap_mirror() as tm1:
            with mock.patch.object(self._plugin, 'get_tap_mirrors',
                                   return_value=[tm1]):
                with self.tap_mirror(directions={"IN": 102}):
                    pass

    def test_same_tunnel_id_different_direction(self):
        with self.tap_mirror() as tm1:
            with mock.patch.object(self._plugin, 'get_tap_mirrors',
                                   return_value=[tm1]):
                with testtools.ExpectedException(
                        taas_exc.TapMirrorTunnelConflict), \
                        self.tap_mirror(directions={"OUT": 101}):
                    pass

    def test_two_direction_tunnel_id(self):
        with self.tap_mirror(directions={'IN': 101, 'OUT': 102}) as tm1:
            with mock.patch.object(self._plugin, 'get_tap_mirrors',
                                   return_value=[tm1]):
                with testtools.ExpectedException(
                        taas_exc.TapMirrorTunnelConflict), \
                        self.tap_mirror(directions={"OUT": 101}):
                    pass

    def test_delete_tap_mrror(self):
        with self.tap_mirror() as tm:
            self._plugin.delete_tap_mirror(self._context, tm['id'])
            self._tap_mirror['id'] = tm['id']

    def test_delete_tap_mirror_non_existent(self):
        with testtools.ExpectedException(taas_exc.TapMirrorNotFound):
            self._plugin.delete_tap_mirror(self._context, 'non-existent')

    # lport mirrors

    def test_create_lport_tap_mirror(self):
        with self.tap_mirror(**self._lport_kwargs) as tm:
            self.assertEqual('lport', tm['mirror_type'])
            self.assertEqual(self._remote_port_id, tm['remote_port_id'])
            self.assertIsNone(tm['remote_ip'])

    def test_create_lport_tap_mirror_without_remote_port(self):
        kwargs = dict(self._lport_kwargs, remote_port_id=None)
        with testtools.ExpectedException(
                taas_exc.TapMirrorRemotePortRequired), \
                self.tap_mirror(**kwargs):
            pass
        self.assertEqual([], self.driver.mock_calls)

    def test_create_lport_tap_mirror_same_port(self):
        kwargs = dict(self._lport_kwargs, remote_port_id=self._port_id)
        with testtools.ExpectedException(
                taas_exc.TapMirrorSameSourceAndRemotePort), \
                self.tap_mirror(**kwargs):
            pass

    def _create_lport_with_remote_port(self, context, remote_details):
        def _details(ctx, port_id):
            if port_id == self._remote_port_id:
                return remote_details
            return self._port_details

        self._tap_mirror.update(self._lport_kwargs)
        with mock.patch.object(self._plugin, 'get_port_details',
                               side_effect=_details):
            return self._plugin.create_tap_mirror(
                context, {'tap_mirror': self._tap_mirror})

    def test_create_lport_tap_mirror_remote_port_not_bound(self):
        remote = dict(self._port_details)
        remote['binding:host_id'] = None
        self.assertRaises(taas_exc.TapMirrorRemotePortNotBound,
                          self._create_lport_with_remote_port,
                          self._context, remote)

    def test_create_lport_tap_mirror_remote_port_other_project(self):
        remote = dict(self._port_details, tenant_id='other-project')
        user_ctx = context.Context('user', self._project_id)
        self.assertRaises(taas_exc.PortDoesNotBelongToProject,
                          self._create_lport_with_remote_port,
                          user_ctx, remote)
        # An admin may mirror into a port of another project.
        tm = self._create_lport_with_remote_port(self._context, remote)
        self.assertEqual(self._remote_port_id, tm['remote_port_id'])

    def _create_lport(self, **kwargs):
        t_m = dict(self._tap_mirror)
        t_m.update(self._lport_kwargs)
        t_m.update(kwargs)
        t_m.pop('id', None)
        with mock.patch.object(self._plugin, 'get_port_details',
                               return_value=self._port_details):
            return self._plugin.create_tap_mirror(self._context,
                                                  {'tap_mirror': t_m})

    def test_create_lport_tap_mirror_port_in_use(self):
        # Only one lport mirror per source port and direction.
        self._create_lport(directions={'IN': None})
        self.assertRaises(taas_exc.TapMirrorLportPortInUse,
                          self._create_lport, directions={'IN': None})
        self.assertRaises(taas_exc.TapMirrorLportPortInUse,
                          self._create_lport, directions={'BOTH': None})
        # The other direction is still free.
        tm_out = self._create_lport(directions={'OUT': None})
        self.assertEqual({'OUT': None}, tm_out['directions'])
        self.assertRaises(taas_exc.TapMirrorLportPortInUse,
                          self._create_lport, directions={'OUT': None})
        # Another source port is not affected.
        tm = self._create_lport(directions={'BOTH': None},
                                port_id=uuidutils.generate_uuid())
        self.assertEqual('lport', tm['mirror_type'])

    def test_create_gre_tap_mirror_without_tunnel_id(self):
        with testtools.ExpectedException(
                taas_exc.TapMirrorTunnelIdRequired), \
                self.tap_mirror(directions={'IN': None}):
            pass

    def test_create_gre_tap_mirror_without_remote_ip(self):
        with testtools.ExpectedException(
                taas_exc.TapMirrorRemoteIpRequired), \
                self.tap_mirror(remote_ip=None):
            pass

    def test_create_gre_tap_mirror_with_remote_port(self):
        with testtools.ExpectedException(
                taas_exc.TapMirrorRemotePortNotAllowed), \
                self.tap_mirror(remote_port_id=self._remote_port_id):
            pass

    def test_delete_remote_port_deletes_lport_tap_mirror(self):
        with self.tap_mirror(**self._lport_kwargs) as tm:
            payload = mock.Mock(context=self._context,
                                latest_state={'id': self._remote_port_id})
            self._plugin.handle_delete_port(None, None, None, payload)
            self.assertRaises(taas_exc.TapMirrorNotFound,
                              self._plugin.get_tap_mirror,
                              self._context, tm['id'])
