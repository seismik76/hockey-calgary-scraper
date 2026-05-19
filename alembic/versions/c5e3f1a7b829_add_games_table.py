"""add games table for completed-game results

Revision ID: c5e3f1a7b829
Revises: b4d2e9f0c1a6
Create Date: 2026-05-18 10:00:00.000000

Stores individual completed games (final scores, date, venue). Previously the
scraper only persisted aggregated team standings; this enables a real
schedule-of-results view for U11 / U13 / U15 from 2024-2025 forward.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5e3f1a7b829'
down_revision: Union[str, None] = 'b4d2e9f0c1a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'games',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('season_id', sa.Integer(), sa.ForeignKey('seasons.id'), nullable=False),
        sa.Column('league_id', sa.Integer(), sa.ForeignKey('leagues.id'), nullable=False),
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('home_score', sa.Integer(), nullable=False),
        sa.Column('away_score', sa.Integer(), nullable=False),
        sa.Column('played_at', sa.DateTime(), nullable=True),
        sa.Column('venue', sa.String(), nullable=True),
        sa.Column('game_type', sa.String(), nullable=True, server_default='Regular'),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_game_id', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.UniqueConstraint('source', 'source_game_id', name='_game_source_uc'),
    )
    # Index for the dominant query: games filtered to one (season, league),
    # ordered by date. Without it, the league-detail page would sequential-scan.
    op.create_index('ix_games_season_league_date', 'games', ['season_id', 'league_id', 'played_at'])


def downgrade() -> None:
    op.drop_index('ix_games_season_league_date', table_name='games')
    op.drop_table('games')
