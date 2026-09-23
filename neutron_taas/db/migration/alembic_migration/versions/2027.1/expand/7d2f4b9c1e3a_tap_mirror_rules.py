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

"""Tap mirror rules

Revision ID: 7d2f4b9c1e3a
Revises: 6c1e2d3a4b5f
Create Date: 2026-09-23 12:00:00.000000

"""

from alembic import op
from neutron_lib.db import constants as db_const

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d2f4b9c1e3a'
down_revision = '6c1e2d3a4b5f'


rule_action_enum = sa.Enum('mirror', 'skip', name='tapmirrorrules_action')
rule_direction_enum = sa.Enum('IN', 'OUT', name='tapmirrorrules_direction')
rule_ethertype_enum = sa.Enum('IPv4', 'IPv6', name='tapmirrorrules_ethertype')


def upgrade():
    op.create_table(
        'tap_mirror_rules',
        sa.Column('id', sa.String(length=db_const.UUID_FIELD_SIZE),
                  primary_key=True),
        sa.Column('project_id', sa.String(
            length=db_const.PROJECT_ID_FIELD_SIZE), nullable=True),
        sa.Column('tap_mirror_id', sa.String(db_const.UUID_FIELD_SIZE),
                  sa.ForeignKey('tap_mirrors.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('action', rule_action_enum, nullable=False),
        sa.Column('direction', rule_direction_enum, nullable=True),
        sa.Column('ethertype', rule_ethertype_enum, nullable=False),
        sa.Column('protocol', sa.String(16), nullable=True),
        sa.Column('source_ip_prefix', sa.String(64), nullable=True),
        sa.Column('destination_ip_prefix', sa.String(64), nullable=True),
        sa.Column('source_port_range_min', sa.Integer(), nullable=True),
        sa.Column('source_port_range_max', sa.Integer(), nullable=True),
        sa.Column('destination_port_range_min', sa.Integer(),
                  nullable=True),
        sa.Column('destination_port_range_max', sa.Integer(),
                  nullable=True),
    )
