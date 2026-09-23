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

from neutron.tests import base
from neutron_lib.api.definitions import tap_mirror as tap_mirror_api
from neutron_lib.api.definitions import tap_mirror_lport as lport_api

from neutron_taas.extensions import tap_mirror_lport as lport_ext


class TapMirrorLportExtensionTestCase(base.BaseTestCase):

    def test_extends_tap_mirrors(self):
        attrs = lport_ext.Tap_mirror_lport().get_extended_resources('2.0')[
            tap_mirror_api.COLLECTION_NAME]
        self.assertIn(lport_api.REMOTE_PORT_ID, attrs)
        self.assertIn(lport_api.MIRROR_TYPE_LPORT,
                      attrs['mirror_type']['validate']['type:values'])
        self.assertIsNone(attrs['remote_ip']['default'])

    def test_no_own_resources(self):
        self.assertEqual([], lport_ext.Tap_mirror_lport().get_resources())
