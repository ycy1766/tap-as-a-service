# Copyright 2026 Openinfra Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sqlalchemy as sa
from sqlalchemy import orm

from neutron_lib.api.definitions import tap_mirror as mirror_extension
from neutron_lib.db import constants as db_const
from neutron_lib.db import model_base

from neutron_taas.extensions import tap_mirror_rules as rules_api_def


class TapMirror(model_base.BASEV2, model_base.HasId,
                model_base.HasProjectNoIndex):
    """Represents a Tap Mirror

    A Tap Mirror can be a GRE or ERSPAN tunnel representation.
    """

    __tablename__ = 'tap_mirrors'

    name = sa.Column(sa.String(db_const.NAME_FIELD_SIZE))
    description = sa.Column(sa.String(db_const.DESCRIPTION_FIELD_SIZE))
    port_id = sa.Column(sa.String(db_const.UUID_FIELD_SIZE),
                        nullable=False)
    directions = sa.Column(sa.String(255), nullable=False)
    remote_ip = sa.Column(sa.String(db_const.IP_ADDR_FIELD_SIZE),
                          nullable=True)
    remote_port_id = sa.Column(sa.String(db_const.UUID_FIELD_SIZE),
                               nullable=True)
    mirror_type = sa.Column(sa.Enum('erspanv1', 'gre', 'lport',
                                    name='tapmirrors_type'),
                            nullable=False)
    api_collections = [mirror_extension.COLLECTION_NAME]
    collection_resource_map = {
        mirror_extension.COLLECTION_NAME: mirror_extension.RESOURCE_NAME}


class TapMirrorRule(model_base.BASEV2, model_base.HasId,
                    model_base.HasProjectNoIndex):
    """Represents a filtering rule of an ``lport`` Tap Mirror.

    Rules are translated by the backend driver into OVN ``Mirror_Rule`` rows:
    the ``priority`` and ``action`` map one to one, the remaining columns
    describe the match of the rule.
    """

    __tablename__ = 'tap_mirror_rules'

    tap_mirror_id = sa.Column(sa.String(db_const.UUID_FIELD_SIZE),
                              sa.ForeignKey('tap_mirrors.id',
                                            ondelete='CASCADE'),
                              nullable=False)
    priority = sa.Column(sa.Integer, nullable=False)
    action = sa.Column(sa.Enum('mirror', 'skip',
                               name='tapmirrorrules_action'),
                       nullable=False)
    # NULL: the rule applies to every direction mirrored by the parent.
    direction = sa.Column(sa.Enum('IN', 'OUT',
                                  name='tapmirrorrules_direction'),
                          nullable=True)
    ethertype = sa.Column(sa.Enum('IPv4', 'IPv6',
                                  name='tapmirrorrules_ethertype'),
                          nullable=False)
    protocol = sa.Column(sa.String(16), nullable=True)
    source_ip_prefix = sa.Column(sa.String(64), nullable=True)
    destination_ip_prefix = sa.Column(sa.String(64), nullable=True)
    source_port_range_min = sa.Column(sa.Integer, nullable=True)
    source_port_range_max = sa.Column(sa.Integer, nullable=True)
    destination_port_range_min = sa.Column(sa.Integer, nullable=True)
    destination_port_range_max = sa.Column(sa.Integer, nullable=True)

    tap_mirror = orm.relationship(
        TapMirror,
        backref=orm.backref('rules', cascade='all, delete-orphan',
                            lazy='selectin'))
    api_collections = [rules_api_def.RULE_COLLECTION_NAME]
    collection_resource_map = {
        rules_api_def.RULE_COLLECTION_NAME: rules_api_def.RULE_RESOURCE_NAME}
