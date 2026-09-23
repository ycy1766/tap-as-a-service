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

from neutron.api import extensions
from neutron.api.v2 import base
from neutron_lib.api.definitions import tap_mirror as tap_mirror_api_def
from neutron_lib.api.definitions import tap_mirror_rules as api_def
from neutron_lib.api import extensions as api_extensions
from neutron_lib.plugins import directory


class Tap_mirror_rules(api_extensions.APIExtensionDescriptor):
    """Filtering rules of ``lport`` tap mirrors.

    Adds the ``rules`` sub-resource of ``tap_mirrors`` used to select the
    traffic mirrored by an ``lport`` tap mirror (``tap-mirror-lport``
    extension).
    """

    api_definition = api_def

    @classmethod
    def get_resources(cls):
        """Return the ``rules`` sub-resource of ``tap_mirrors``.

        The ``tap_mirrors`` collection itself is provided by the
        ``tap-mirror`` extension.
        """
        plugin = directory.get_plugin(tap_mirror_api_def.ALIAS)
        resources = []
        for collection_name, collection in (
                api_def.SUB_RESOURCE_ATTRIBUTE_MAP.items()):
            resource_name = collection_name[:-1]
            parent = collection.get('parent')
            params = collection.get('parameters')

            controller = base.create_resource(
                collection_name, resource_name, plugin, params,
                allow_bulk=False, parent=parent,
                allow_pagination=True, allow_sorting=True)

            resources.append(extensions.ResourceExtension(
                collection_name, controller, parent,
                path_prefix='/taas', attr_map=params))
        return resources
