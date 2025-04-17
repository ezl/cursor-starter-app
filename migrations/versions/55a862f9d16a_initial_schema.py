"""initial schema

Revision ID: 55a862f9d16a
Revises: 
Create Date: 2025-04-16 22:11:42.728159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '55a862f9d16a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('password', sa.String(length=128), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('auth_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=100), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('used', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('auth_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auth_tokens_token'), ['token'], unique=True)

    op.create_table('posts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('published', sa.Boolean(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('trips',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('destination', sa.String(length=255), nullable=False),
    sa.Column('traveler_name', sa.String(length=100), nullable=True),
    sa.Column('share_token', sa.String(length=64), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('trips', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_trips_share_token'), ['share_token'], unique=True)
        batch_op.create_index(batch_op.f('ix_trips_slug'), ['slug'], unique=True)

    op.create_table('recommendations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('place_type', sa.String(length=50), nullable=True),
    sa.Column('website_url', sa.String(length=255), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('trip_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('recommendations')
    with op.batch_alter_table('trips', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_trips_slug'))
        batch_op.drop_index(batch_op.f('ix_trips_share_token'))

    op.drop_table('trips')
    op.drop_table('posts')
    with op.batch_alter_table('auth_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_tokens_token'))

    op.drop_table('auth_tokens')
    op.drop_table('users')
    # ### end Alembic commands ### 