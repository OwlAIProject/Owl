"""Add person and voicesamples

Revision ID: b6aff0a993d7
Revises: 33bddba74d25
Create Date: 2024-03-01 08:56:55.205553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel 


# revision identifiers, used by Alembic.
revision: str = 'b6aff0a993d7'
down_revision: Union[str, None] = '33bddba74d25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch operations to support SQLite ALTER TABLE for adding constraints
    with op.batch_alter_table('utterance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_utterance_person', 'person', ['person_id'], ['id'])

    op.create_table('person',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('last_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('voicesample',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filepath', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('speaker_embeddings', sa.JSON(), nullable=True),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['person.id'], name='fk_voicesample_person'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    # Use batch operations for dropping column with SQLite
    with op.batch_alter_table('utterance', schema=None) as batch_op:
        batch_op.drop_constraint('fk_utterance_person', type_='foreignkey')
        batch_op.drop_column('person_id')

    # Commands for dropping tables remain unchanged
    op.drop_table('voicesample')
    op.drop_table('person')