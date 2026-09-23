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

import sys

from neutron.api import extensions
from neutron.api.v2 import base
from neutron_lib.api import converters
from neutron_lib.api.definitions import taas
from neutron_lib.api.definitions import tap_mirror
from neutron_lib.api import extensions as api_extensions
from neutron_lib import constants
from neutron_lib.db import constants as db_const
from neutron_lib import exceptions as n_exc
from neutron_lib.plugins import directory

from neutron_taas._i18n import _
from neutron_taas.extensions import tap_mirror_lport

# TODO(ycy1766): use the API definition and the exceptions from neutron-lib
# once the neutron-lib change that adds them (Change-Id
# I45438ce2e565ba66e5ba48d09f912eb7b4379703) is merged and released. Until
# then they are carried here, like for the ``tap-mirror-lport`` extension.

ALIAS = 'tap-mirror-rules'
IS_SHIM_EXTENSION = False
IS_STANDARD_ATTR_EXTENSION = False
NAME = "Tap as a Service mirror filtering rules"
DESCRIPTION = ("Neutron Tap as a Service extension to select the traffic "
               "mirrored by an lport tap mirror with priority ordered "
               "rules.")
UPDATED_TIMESTAMP = "2026-09-23T10:00:00-00:00"

# Filtering rules sub-resource: /taas/tap_mirrors/{id}/rules
RULE_RESOURCE_NAME = 'rule'
RULE_COLLECTION_NAME = 'rules'
RULE_PARENT = {
    'collection_name': tap_mirror.COLLECTION_NAME,
    'member_name': tap_mirror.RESOURCE_NAME,
}

RULE_ACTION_MIRROR = 'mirror'
RULE_ACTION_SKIP = 'skip'
RULE_ACTIONS = [RULE_ACTION_MIRROR, RULE_ACTION_SKIP]

# OVN Mirror_Rule priority range. The backend keeps priority 0 for the
# implicit "mirror everything" flow of the mirror, so user rules start at 1.
RULE_PRIORITY_MIN = 1
RULE_PRIORITY_MAX = 32767

# A rule applies to both mirrored directions unless ``direction`` selects
# one of them.
RULE_DIRECTIONS = [taas.DIRECTION_IN, taas.DIRECTION_OUT]

RULE_ETHERTYPES = [constants.IPv4, constants.IPv6]
RULE_PROTOCOLS = [
    constants.PROTO_NAME_TCP,
    constants.PROTO_NAME_UDP,
    constants.PROTO_NAME_SCTP,
    constants.PROTO_NAME_ICMP,
    constants.PROTO_NAME_IPV6_ICMP,
]

RESOURCE_ATTRIBUTE_MAP = {}

SUB_RESOURCE_ATTRIBUTE_MAP = {
    RULE_COLLECTION_NAME: {
        'parent': RULE_PARENT,
        'parameters': {
            'id': {
                'allow_post': False,
                'allow_put': False,
                'validate': {'type:uuid': None},
                'is_visible': True,
                'is_filter': True,
                'is_sort_key': True,
                'primary_key': True
            },
            'project_id': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                'required_by_policy': True,
                'is_visible': True,
                'is_filter': True
            },
            'priority': {
                'allow_post': True,
                'allow_put': False,
                'convert_to': converters.convert_to_int,
                'validate': {
                    'type:range': (RULE_PRIORITY_MIN, RULE_PRIORITY_MAX)},
                'is_visible': True,
                'is_filter': True,
                'is_sort_key': True
            },
            'action': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:values': RULE_ACTIONS},
                'default': RULE_ACTION_MIRROR,
                'is_visible': True,
                'is_filter': True
            },
            'direction': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:values': RULE_DIRECTIONS + [None]},
                'default': None,
                'is_visible': True,
                'is_filter': True
            },
            # Optional: a rule without ethertype matches every frame, and
            # the ethertype can be derived from the IP prefixes.
            'ethertype': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:values': RULE_ETHERTYPES + [None]},
                'default': None,
                'is_visible': True,
                'is_filter': True
            },
            'protocol': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:values': RULE_PROTOCOLS + [None]},
                'default': None,
                'is_visible': True,
                'is_filter': True
            },
            'source_ip_prefix': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:subnet_or_none': None},
                'default': None,
                'is_visible': True,
                'is_filter': True
            },
            'destination_ip_prefix': {
                'allow_post': True,
                'allow_put': False,
                'validate': {'type:subnet_or_none': None},
                'default': None,
                'is_visible': True,
                'is_filter': True
            },
            'source_port_range_min': {
                'allow_post': True,
                'allow_put': False,
                'convert_to': converters.convert_to_int_if_not_none,
                'validate': {'type:range_or_none': (1, 65535)},
                'default': None,
                'is_visible': True
            },
            'source_port_range_max': {
                'allow_post': True,
                'allow_put': False,
                'convert_to': converters.convert_to_int_if_not_none,
                'validate': {'type:range_or_none': (1, 65535)},
                'default': None,
                'is_visible': True
            },
            'destination_port_range_min': {
                'allow_post': True,
                'allow_put': False,
                'convert_to': converters.convert_to_int_if_not_none,
                'validate': {'type:range_or_none': (1, 65535)},
                'default': None,
                'is_visible': True
            },
            'destination_port_range_max': {
                'allow_post': True,
                'allow_put': False,
                'convert_to': converters.convert_to_int_if_not_none,
                'validate': {'type:range_or_none': (1, 65535)},
                'default': None,
                'is_visible': True
            },
        }
    }
}

ACTION_MAP = {}
ACTION_STATUS = {}
REQUIRED_EXTENSIONS = [tap_mirror.ALIAS, tap_mirror_lport.ALIAS]
OPTIONAL_EXTENSIONS = []


class TapMirrorRuleNotFound(n_exc.NotFound):
    message = _("Tap Mirror rule %(rule_id)s does not exist")


class TapMirrorRulesNotSupported(n_exc.InvalidInput):
    message = _("Tap Mirror %(mirror_id)s of type %(mirror_type)s does not "
                "support rules")


class TapMirrorRuleConflict(n_exc.Conflict):
    message = _("Tap Mirror %(mirror_id)s already has a rule with priority "
                "%(priority)s and the same match")


class TapMirrorRuleInvalidPortRange(n_exc.InvalidInput):
    message = _("Invalid port range in Tap Mirror rule: %(reason)s")


class TapMirrorRuleInvalidMatch(n_exc.InvalidInput):
    message = _("Invalid match in Tap Mirror rule: %(reason)s")


class TapMirrorRuleDirectionNotMirrored(n_exc.InvalidInput):
    message = _("Tap Mirror %(mirror_id)s does not mirror direction "
                "%(direction)s")


class Tap_mirror_rules(api_extensions.APIExtensionDescriptor):
    """Filtering rules of ``lport`` tap mirrors.

    Adds the ``rules`` sub-resource of ``tap_mirrors`` used to select the
    traffic mirrored by an ``lport`` tap mirror (``tap-mirror-lport``
    extension).
    """

    api_definition = sys.modules[__name__]

    @classmethod
    def get_resources(cls):
        """Return the ``rules`` sub-resource of ``tap_mirrors``.

        The ``tap_mirrors`` collection itself is provided by the
        ``tap-mirror`` extension.
        """
        plugin = directory.get_plugin(tap_mirror.ALIAS)
        resources = []
        for collection_name, collection in (
                SUB_RESOURCE_ATTRIBUTE_MAP.items()):
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
