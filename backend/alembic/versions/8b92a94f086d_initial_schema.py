"""initial_schema

Revision ID: 8b92a94f086d
Revises: 
Create Date: 2026-07-30 02:42:39.744372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8b92a94f086d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, default='viewer', index=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('force_password_change', sa.Boolean(), nullable=False, default=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('token_version', sa.Integer(), nullable=False, default=0),
    )

    # ── products ──
    op.create_table(
        'products',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('sku', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('product_name_zh', sa.String(200), nullable=False),
        sa.Column('product_name_en', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('brand', sa.String(50), nullable=True),
        sa.Column('description_zh', sa.Text(), nullable=True),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('stock', sa.Integer(), nullable=True),
        sa.Column('color_zh', sa.String(100), nullable=True),
        sa.Column('color_en', sa.String(100), nullable=True),
        sa.Column('material_zh', sa.String(100), nullable=True),
        sa.Column('material_en', sa.String(100), nullable=True),
        sa.Column('size', sa.String(100), nullable=True),
        sa.Column('weight', sa.Numeric(10, 2), nullable=True),
        sa.Column('weight_unit', sa.String(10), nullable=True, default='kg'),
        sa.Column('length', sa.Numeric(10, 2), nullable=True),
        sa.Column('width', sa.Numeric(10, 2), nullable=True),
        sa.Column('height', sa.Numeric(10, 2), nullable=True),
        sa.Column('dimension_unit', sa.String(10), nullable=True, default='cm'),
        sa.Column('origin', sa.String(50), nullable=True, default='China'),
        sa.Column('model_number', sa.String(64), nullable=True),
        sa.Column('extra_fields', sa.JSON(), nullable=True),
        sa.Column('consistency_status', sa.String(20), nullable=False, default='unchecked'),
        sa.Column('consistency_issues', sa.JSON(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_product_name_search', 'products', ['product_name_zh', 'product_name_en'])
    op.create_index('idx_product_created_by', 'products', ['created_by'])
    op.create_index('idx_product_is_deleted', 'products', ['is_deleted'])

    # ── term_dictionary ──
    op.create_table(
        'term_dictionary',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('zh', sa.String(100), nullable=False),
        sa.Column('en', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('synonyms', sa.JSON(), nullable=False),
        sa.Column('platform_amazon', sa.String(100), nullable=True),
        sa.Column('platform_alibaba', sa.String(100), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, default=True, index=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_term_zh_en', 'term_dictionary', ['zh', 'en'], unique=True)

    # ── audit_logs ──
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(64), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])

    # ── refresh_token_blacklist ──
    op.create_table(
        'refresh_token_blacklist',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('token_id', sa.String(36), unique=True, nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_token_blacklist_user_expires', 'refresh_token_blacklist', ['user_id', 'expires_at'])


def downgrade() -> None:
    op.drop_table('refresh_token_blacklist')
    op.drop_table('audit_logs')
    op.drop_table('term_dictionary')
    op.drop_table('products')
    op.drop_table('users')
