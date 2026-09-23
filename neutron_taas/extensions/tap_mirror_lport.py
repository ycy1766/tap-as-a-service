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

from neutron_lib.api.definitions import tap_mirror_lport as api_def
from neutron_lib.api import extensions as api_extensions


class Tap_mirror_lport(api_extensions.APIExtensionDescriptor):
    """Mirror the traffic of a port to another Neutron port (OVN lport).

    Extends ``tap_mirrors`` with the ``lport`` mirror type and the
    ``remote_port_id`` attribute. The ``tap_mirrors`` collection itself is
    provided by the ``tap-mirror`` extension.
    """

    api_definition = api_def
