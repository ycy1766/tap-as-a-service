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

"""Tap mirror to a logical port (lport)

Revision ID: 6c1e2d3a4b5f
Revises: f8f1f10ebaf9
Create Date: 2026-09-22 20:00:00.000000

"""

from alembic import op
from neutron.db import migration
from neutron_lib.db import constants as db_const

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c1e2d3a4b5f'
down_revision = 'f8f1f10ebaf9'


mirror_type_enum = sa.Enum('erspanv1', 'gre', 'lport',
                           name='tapmirrors_type')


def upgrade():
    # SQLite stores Enum values in a VARCHAR column without a CHECK
    # constraint, so widening the enumeration is only needed elsewhere.
    if op.get_bind().engine.name != 'sqlite':
        migration.alter_enum_add_value('tap_mirrors', 'mirror_type',
                                       mirror_type_enum, nullable=False)
    op.add_column(
        'tap_mirrors',
        sa.Column('remote_port_id', sa.String(db_const.UUID_FIELD_SIZE),
                  nullable=True))
