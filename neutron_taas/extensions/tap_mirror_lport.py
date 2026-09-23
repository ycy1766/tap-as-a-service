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

from neutron_lib.api.definitions import taas
from neutron_lib.api.definitions import tap_mirror
from neutron_lib.api import extensions as api_extensions
from neutron_lib import exceptions as n_exc

from neutron_taas._i18n import _
from neutron_taas.extensions import tap_mirror_both_direction

# TODO(ycy1766): use the API definition and the exceptions from neutron-lib
# once https://review.opendev.org/c/openstack/neutron-lib/+/1009192 is
# merged and released. Until then they are carried here, as was done for the
# ``tap-mirror-both-direction`` extension.

ALIAS = 'tap-mirror-lport'
IS_SHIM_EXTENSION = False
IS_STANDARD_ATTR_EXTENSION = False
NAME = "Tap as a Service mirror to a logical port"
DESCRIPTION = ("Neutron Tap as a Service extension to mirror the traffic of a "
               "port to another Neutron port inside the overlay.")
UPDATED_TIMESTAMP = "2026-09-22T10:00:00-00:00"

# New mirror type: the sink of the mirror is a Neutron port (an OVN logical
# switch port) instead of a remote IP address. The mirrored frames are
# delivered inside the overlay without any tunnel encapsulation.
MIRROR_TYPE_LPORT = 'lport'
mirror_types_list = tap_mirror.mirror_types_list + [MIRROR_TYPE_LPORT]

REMOTE_PORT_ID = 'remote_port_id'

# Redefines ``directions`` of the ``tap-mirror-both-direction`` extension
# (``IN``, ``OUT`` and ``BOTH`` keys) with optional tunnel ID values. The
# tunnel IDs are meaningless for an ``lport`` mirror, so
# ``{"IN": null, "OUT": null}`` or ``{"BOTH": null}`` only selects the
# mirrored directions. The service plugin checks the values per mirror type:
# ``gre``/``erspanv1`` mirrors still need a tunnel ID per direction,
# ``lport`` mirrors must not carry one.
TUNNEL_ID_MAX = 2 ** 32 - 1
DIRECTION_SPEC = {
    'type:dict': {
        taas.DIRECTION_IN: {'type:range_or_none': (0, TUNNEL_ID_MAX),
                            'default': None, 'required': False},
        taas.DIRECTION_OUT: {'type:range_or_none': (0, TUNNEL_ID_MAX),
                             'default': None, 'required': False},
        taas.DIRECTION_BOTH: {'type:range_or_none': (0, TUNNEL_ID_MAX),
                              'default': None, 'required': False},
    }
}

RESOURCE_ATTRIBUTE_MAP = {
    tap_mirror.COLLECTION_NAME: {
        'mirror_type': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:values': mirror_types_list},
            'is_visible': True,
            'is_filter': True
        },
        'directions': {
            'allow_post': True,
            'allow_put': False,
            'validate': DIRECTION_SPEC,
            'is_visible': True
        },
        # Still mandatory for ``gre``/``erspanv1`` mirrors, must be unset
        # for the ``lport`` mirror type (checked by the service plugin).
        'remote_ip': {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:ip_address_or_none': None},
            'default': None,
            'is_visible': True,
            'is_filter': True
        },
        # The Neutron port that receives the mirrored traffic. Mandatory for
        # the ``lport`` mirror type, must be unset for the other types.
        REMOTE_PORT_ID: {
            'allow_post': True,
            'allow_put': False,
            'validate': {'type:uuid_or_none': None},
            'default': None,
            'is_visible': True,
            'is_filter': True
        },
    }
}

SUB_RESOURCE_ATTRIBUTE_MAP = None
ACTION_MAP = {}
ACTION_STATUS = {}
REQUIRED_EXTENSIONS = [tap_mirror.ALIAS, tap_mirror_both_direction.ALIAS]
OPTIONAL_EXTENSIONS = []


class TapMirrorRemotePortRequired(n_exc.InvalidInput):
    message = _("Tap Mirror of type %(mirror_type)s requires remote_port_id")


class TapMirrorRemoteIpRequired(n_exc.InvalidInput):
    message = _("Tap Mirror of type %(mirror_type)s requires remote_ip")


class TapMirrorRemotePortNotAllowed(n_exc.InvalidInput):
    message = _("Tap Mirror of type %(mirror_type)s does not accept "
                "remote_port_id")


class TapMirrorRemoteIpNotAllowed(n_exc.InvalidInput):
    message = _("Tap Mirror of type %(mirror_type)s does not accept "
                "remote_ip")


class TapMirrorTunnelIdNotAllowed(n_exc.InvalidInput):
    message = _("Tap Mirror of type %(mirror_type)s does not accept a tunnel "
                "ID for direction %(direction)s")


class TapMirrorSameSourceAndRemotePort(n_exc.InvalidInput):
    message = _("Tap Mirror source port and remote port must differ")


class TapMirrorRemotePortNotBound(n_exc.InvalidInput):
    message = _("Tap Mirror remote port %(port_id)s is not bound to a host")


class TapMirrorTunnelIdRequired(n_exc.InvalidInput):
    message = _("Tap Mirror of type %(mirror_type)s requires a tunnel ID for "
                "direction %(direction)s")


class TapMirrorLportPortInUse(n_exc.Conflict):
    message = _("Port %(port_id)s already has an lport Tap Mirror for "
                "direction %(direction)s")


class Tap_mirror_lport(api_extensions.ExtensionDescriptor):
    """Mirror the traffic of a port to another Neutron port (OVN lport).

    Extends ``tap_mirrors`` with the ``lport`` mirror type and the
    ``remote_port_id`` attribute. The ``tap_mirrors`` collection itself is
    provided by the ``tap-mirror`` extension.
    """

    @classmethod
    def get_name(cls):
        return NAME

    @classmethod
    def get_alias(cls):
        return ALIAS

    @classmethod
    def get_description(cls):
        return DESCRIPTION

    @classmethod
    def get_updated(cls):
        return UPDATED_TIMESTAMP

    def get_required_extensions(self):
        return REQUIRED_EXTENSIONS

    def get_extended_resources(self, version):
        if version == "2.0":
            return RESOURCE_ATTRIBUTE_MAP
        return {}
