"""Add pontuacao column to simulado_questoes table

Revision ID: add_pontuacao_to_simulado_questoes
Revises: 
Create Date: 2025-02-24 16:12:27.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_pontuacao_to_simulado_questoes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Adicionar coluna pontuacao com valor padrão 1.0
    op.add_column('simulado_questoes', sa.Column('pontuacao', sa.Float(), nullable=False, server_default='1.0'))

def downgrade():
    # Remover coluna pontuacao
    op.drop_column('simulado_questoes', 'pontuacao')
