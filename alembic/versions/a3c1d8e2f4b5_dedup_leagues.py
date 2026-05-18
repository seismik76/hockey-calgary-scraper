"""dedup duplicate leagues by (name, stream, type)

Revision ID: a3c1d8e2f4b5
Revises: f7500685a0fe
Create Date: 2026-05-17 21:00:00.000000

Background:
TeamLinkt's hierarchy_filter dropdown exposes some leagues under two
hierarchy IDs (e.g. `260972-260985` and `249020-249139`). Because the
`leagues` unique constraint only covered (slug, stream, type), the scraper
inserted each as a distinct league row — and then wrote duplicate standings
rows under the second league_id. This migration:

  1. For each duplicate (name, stream, type) group, picks a winner — the
     league with the most standings, ties broken by the highest numeric
     slug prefix (which matches the scraper's go-forward dedup rule).
  2. For each loser:
     a. Drops loser `standings` rows that would conflict with a winner row
        on (season_id, team_id) — those are the actual duplicates.
     b. Repoints remaining loser standings to the winner.
     c. Deletes the loser `leagues` row.
  3. Adds a new UNIQUE constraint on (name, stream, type) so the scraper
     can't quietly re-introduce duplicates if its in-process dedup ever
     misses a case.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c1d8e2f4b5'
down_revision: Union[str, None] = 'f7500685a0fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Find every (name, stream, type) group with more than one league row.
    groups = conn.execute(
        sa.text(
            """
            SELECT name, stream, type
            FROM leagues
            GROUP BY name, stream, type
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    print(f"  dedup_leagues: found {len(groups)} duplicate league group(s)")

    total_dropped_standings = 0
    total_repointed_standings = 0
    total_deleted_leagues = 0

    for group in groups:
        # 2. Rank candidates in this group: most standings first, then highest
        #    numeric slug prefix as a tiebreaker. The top row is the winner.
        candidates = conn.execute(
            sa.text(
                """
                SELECT l.id, l.slug, COUNT(st.id) AS standings_count
                FROM leagues l
                LEFT JOIN standings st ON st.league_id = l.id
                WHERE l.name = :name AND l.stream = :stream AND l.type = :type
                GROUP BY l.id, l.slug
                """
            ),
            {'name': group.name, 'stream': group.stream, 'type': group.type},
        ).fetchall()

        def slug_prefix(slug: str) -> int:
            try:
                return int(slug.split('-', 1)[0])
            except (ValueError, AttributeError):
                return 0

        ranked = sorted(
            candidates,
            key=lambda c: (c.standings_count, slug_prefix(c.slug)),
            reverse=True,
        )
        winner = ranked[0]
        losers = ranked[1:]

        for loser in losers:
            # 2a. Drop loser standings that already have a winner-side row
            #     for the same (season, team). These are the true duplicates.
            dropped = conn.execute(
                sa.text(
                    """
                    DELETE FROM standings
                    WHERE league_id = :loser_id
                      AND (season_id, team_id) IN (
                          SELECT season_id, team_id
                          FROM standings
                          WHERE league_id = :winner_id
                      )
                    """
                ),
                {'loser_id': loser.id, 'winner_id': winner.id},
            ).rowcount or 0
            total_dropped_standings += dropped

            # 2b. Repoint anything left under loser → winner. With unique
            #     (season, league, team), any survivor here is unique vs
            #     the winner side, so the UPDATE is safe.
            repointed = conn.execute(
                sa.text(
                    """
                    UPDATE standings
                    SET league_id = :winner_id
                    WHERE league_id = :loser_id
                    """
                ),
                {'loser_id': loser.id, 'winner_id': winner.id},
            ).rowcount or 0
            total_repointed_standings += repointed

            # 2c. Delete loser league row.
            conn.execute(
                sa.text("DELETE FROM leagues WHERE id = :loser_id"),
                {'loser_id': loser.id},
            )
            total_deleted_leagues += 1

    print(
        f"  dedup_leagues: dropped {total_dropped_standings} duplicate standings, "
        f"repointed {total_repointed_standings}, deleted {total_deleted_leagues} loser leagues"
    )

    # 3. Add the new semantic unique constraint now that the data is clean.
    op.create_unique_constraint(
        '_league_name_stream_type_uc',
        'leagues',
        ['name', 'stream', 'type'],
    )


def downgrade() -> None:
    # We can't recreate the deleted duplicate rows — they were lossy by
    # design. Just drop the new constraint so the schema reverts.
    op.drop_constraint(
        '_league_name_stream_type_uc',
        'leagues',
        type_='unique',
    )
