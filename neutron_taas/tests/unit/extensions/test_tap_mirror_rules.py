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

import copy
from unittest import mock

from webob import exc

from oslo_utils import uuidutils

from neutron.api import extensions
from neutron.conf import common as conf_common
from neutron.tests.unit.api.v2 import test_base as test_api_v2
from neutron.tests.unit.extensions import base as test_extensions_base
from neutron_lib.api.definitions import tap_mirror as tap_mirror_api

from neutron_taas import extensions as taas_extensions
from neutron_taas.extensions import tap_mirror as tap_mirror_ext
from neutron_taas.extensions import tap_mirror_rules as rules_ext

TAP_MIRROR_PATH = 'taas/tap_mirrors'


class TapMirrorRulesExtensionTestCase(test_extensions_base.ExtensionTestCase):

    def setUp(self):
        conf_common.register_core_common_config_opts()
        extensions.append_api_extensions_path(taas_extensions.__path__)
        super().setUp()
        plural_mappings = {'tap_mirror': 'tap_mirrors', 'rule': 'rules'}
        self.setup_extension(
            '%s.%s' % (tap_mirror_ext.TapMirrorBase.__module__,
                       tap_mirror_ext.TapMirrorBase.__name__),
            tap_mirror_api.ALIAS,
            rules_ext.Tap_mirror_rules,
            'taas',
            plural_mappings=plural_mappings,
            translate_resource_name=False)
        self.instance = self.plugin.return_value
        self.tap_mirror_id = uuidutils.generate_uuid()
        self.rules_path = '%s/%s/rules' % (TAP_MIRROR_PATH,
                                           self.tap_mirror_id)

    def test_create_tap_mirror_rule(self):
        project_id = uuidutils.generate_uuid()
        rule_data = {
            'project_id': project_id,
            'tenant_id': project_id,
            'priority': 100,
            'action': 'mirror',
            'direction': 'IN',
            'ethertype': 'IPv4',
            'protocol': 'tcp',
            'source_ip_prefix': None,
            'destination_ip_prefix': '10.0.0.0/24',
            'source_port_range_min': None,
            'source_port_range_max': None,
            'destination_port_range_min': 443,
            'destination_port_range_max': 443,
        }
        data = {'rule': rule_data}
        expected_ret_val = copy.copy(rule_data)
        expected_ret_val.update({'id': uuidutils.generate_uuid()})
        self.instance.create_tap_mirror_rule.return_value = expected_ret_val

        res = self.api.post(test_api_v2._get_path(self.rules_path,
                                                  fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/%s' % self.fmt)

        self.instance.create_tap_mirror_rule.assert_called_with(
            mock.ANY, tap_mirror_id=self.tap_mirror_id, rule=data)
        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        res = self.deserialize(res)
        self.assertIn('rule', res)
        self.assertEqual(expected_ret_val, res['rule'])

    def test_create_tap_mirror_rule_defaults(self):
        project_id = uuidutils.generate_uuid()
        data = {'rule': {'project_id': project_id, 'priority': 1,
                         'action': 'skip'}}
        self.instance.create_tap_mirror_rule.return_value = dict(
            data['rule'], id=uuidutils.generate_uuid())

        res = self.api.post(test_api_v2._get_path(self.rules_path,
                                                  fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/%s' % self.fmt)

        self.assertEqual(exc.HTTPCreated.code, res.status_int)
        sent = self.instance.create_tap_mirror_rule.call_args[1]['rule']
        self.assertEqual('IPv4', sent['rule']['ethertype'])
        self.assertIsNone(sent['rule']['direction'])
        self.assertIsNone(sent['rule']['protocol'])
        self.assertIsNone(sent['rule']['destination_port_range_max'])

    def test_create_tap_mirror_rule_invalid_priority(self):
        # 0 is reserved for the implicit "mirror everything" flow.
        for priority in (0, 40000):
            data = {'rule': {'project_id': uuidutils.generate_uuid(),
                             'priority': priority}}
            res = self.api.post(test_api_v2._get_path(self.rules_path,
                                                      fmt=self.fmt),
                                self.serialize(data),
                                content_type='application/%s' % self.fmt,
                                expect_errors=True)
            self.assertEqual(exc.HTTPBadRequest.code, res.status_int)
        self.instance.create_tap_mirror_rule.assert_not_called()

    def test_create_tap_mirror_rule_invalid_direction(self):
        data = {'rule': {'project_id': uuidutils.generate_uuid(),
                         'priority': 10, 'direction': 'BOTH'}}
        res = self.api.post(test_api_v2._get_path(self.rules_path,
                                                  fmt=self.fmt),
                            self.serialize(data),
                            content_type='application/%s' % self.fmt,
                            expect_errors=True)
        self.assertEqual(exc.HTTPBadRequest.code, res.status_int)
        self.instance.create_tap_mirror_rule.assert_not_called()

    def test_list_tap_mirror_rules(self):
        rule = {'id': uuidutils.generate_uuid(), 'priority': 10,
                'action': 'mirror'}
        self.instance.get_tap_mirror_rules.return_value = [rule]
        res = self.api.get(test_api_v2._get_path(self.rules_path,
                                                 fmt=self.fmt))
        self.instance.get_tap_mirror_rules.assert_called_with(
            mock.ANY, tap_mirror_id=self.tap_mirror_id, fields=mock.ANY,
            filters=mock.ANY)
        self.assertEqual(exc.HTTPOk.code, res.status_int)
        res = self.deserialize(res)
        self.assertEqual([rule], res['rules'])

    def test_delete_tap_mirror_rule(self):
        rule_id = uuidutils.generate_uuid()
        res = self.api.delete(test_api_v2._get_path(
            '%s/%s' % (self.rules_path, rule_id), fmt=self.fmt))
        self.instance.delete_tap_mirror_rule.assert_called_with(
            mock.ANY, rule_id, tap_mirror_id=self.tap_mirror_id)
        self.assertEqual(exc.HTTPNoContent.code, res.status_int)
