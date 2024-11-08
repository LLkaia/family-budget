"""timestamp in transactions

Revision ID: 58a364e34185
Revises: 1549c7102341
Create Date: 2024-10-13 12:05:32.741998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '58a364e34185'
down_revision: Union[str, None] = '1549c7102341'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('date_performed', sa.Date(), nullable=False))
    op.add_column('transaction', sa.Column('datetime_added', sa.DateTime(), nullable=False))
    op.drop_column('transaction', 'date')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False))
    op.drop_column('transaction', 'datetime_added')
    op.drop_column('transaction', 'date_performed')
    # ### end Alembic commands ###
