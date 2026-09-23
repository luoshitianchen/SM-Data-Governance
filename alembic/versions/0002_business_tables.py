"""新增业务表：数据资产、数据血缘与质量规则。

Revision ID: 0002_business_tables
Revises: 0001_initial
Create Date: 2026-09-23
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# 本迁移的版本号，下游 0003 及以后迁移以此为 down_revision
revision: str = '0002_business_tables'
# 上一版本，承接 0001_initial
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Alembic 自动生成开始，按模型元数据建立业务表 ###
    # 数据资产表：登记纳入治理的数据资产
    op.create_table('data_assets',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('category', sa.String(length=64), nullable=False),
    sa.Column('owner', sa.String(length=80), nullable=False),
    sa.Column('sensitivity', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_assets_category'), 'data_assets', ['category'], unique=False)
    op.create_index(op.f('ix_data_assets_code'), 'data_assets', ['code'], unique=True)
    op.create_index(op.f('ix_data_assets_sensitivity'), 'data_assets', ['sensitivity'], unique=False)
    op.create_index(op.f('ix_data_assets_status'), 'data_assets', ['status'], unique=False)
    # 数据血缘表：记录资产间上下游流转关系
    op.create_table('data_lineages',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('upstream_code', sa.String(length=64), nullable=False),
    sa.Column('downstream_code', sa.String(length=64), nullable=False),
    sa.Column('relation_type', sa.String(length=32), nullable=False),
    sa.Column('transform_logic', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('upstream_code', 'downstream_code', 'relation_type', name='uq_lineage_edge')
    )
    op.create_index(op.f('ix_data_lineages_downstream_code'), 'data_lineages', ['downstream_code'], unique=False)
    op.create_index(op.f('ix_data_lineages_relation_type'), 'data_lineages', ['relation_type'], unique=False)
    op.create_index(op.f('ix_data_lineages_upstream_code'), 'data_lineages', ['upstream_code'], unique=False)
    # 数据质量规则表：定义资产的数据质量校验规则
    op.create_table('quality_rules',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('asset_code', sa.String(length=64), nullable=False),
    sa.Column('rule_type', sa.String(length=32), nullable=False),
    sa.Column('expression', sa.Text(), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quality_rules_asset_code'), 'quality_rules', ['asset_code'], unique=False)
    op.create_index(op.f('ix_quality_rules_code'), 'quality_rules', ['code'], unique=True)
    op.create_index(op.f('ix_quality_rules_rule_type'), 'quality_rules', ['rule_type'], unique=False)
    op.create_index(op.f('ix_quality_rules_severity'), 'quality_rules', ['severity'], unique=False)
    op.create_index(op.f('ix_quality_rules_status'), 'quality_rules', ['status'], unique=False)
    # ### Alembic 自动生成结束 ###


def downgrade() -> None:
    # ### Alembic 自动生成开始，按逆序删除业务表与索引 ###
    op.drop_index(op.f('ix_quality_rules_status'), table_name='quality_rules')
    op.drop_index(op.f('ix_quality_rules_severity'), table_name='quality_rules')
    op.drop_index(op.f('ix_quality_rules_rule_type'), table_name='quality_rules')
    op.drop_index(op.f('ix_quality_rules_code'), table_name='quality_rules')
    op.drop_index(op.f('ix_quality_rules_asset_code'), table_name='quality_rules')
    op.drop_table('quality_rules')
    op.drop_index(op.f('ix_data_lineages_upstream_code'), table_name='data_lineages')
    op.drop_index(op.f('ix_data_lineages_relation_type'), table_name='data_lineages')
    op.drop_index(op.f('ix_data_lineages_downstream_code'), table_name='data_lineages')
    op.drop_table('data_lineages')
    op.drop_index(op.f('ix_data_assets_status'), table_name='data_assets')
    op.drop_index(op.f('ix_data_assets_sensitivity'), table_name='data_assets')
    op.drop_index(op.f('ix_data_assets_code'), table_name='data_assets')
    op.drop_index(op.f('ix_data_assets_category'), table_name='data_assets')
    op.drop_table('data_assets')
    # ### Alembic 自动生成结束 ###
