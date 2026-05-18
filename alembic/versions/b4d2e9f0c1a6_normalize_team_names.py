"""normalize team-name casing + merge case-variant duplicate teams

Revision ID: b4d2e9f0c1a6
Revises: a3c1d8e2f4b5
Create Date: 2026-05-17 21:30:00.000000

Background:
RAMP / Alberta One scrapes report team names in ALL CAPS (`KNIGHTS U11 AA`).
City Championships / Esso tournament scrapes report mixed case
(`Knights U11 AA`). Both variants got stored as distinct rows in the teams
table because the uniqueness check on `name` is case-sensitive, splitting
standings for the same physical team across two team_ids.

This migration:

  1. Merges every team-pair where LOWER(TRIM(name)) collides: pick the
     mixed-case variant (or the row with more standings, breaking ties)
     as the winner, drop loser standings that would conflict on
     (season_id, league_id), repoint the rest, then delete the loser
     team row.
  2. Renames remaining all-caps team rows in place to the normalised
     casing, keeping hockey acronyms (`AA`, `HADP`, `NBC`, `BC`) and
     digit-bearing tokens (`U11`, `U13`) intact.

Going forward, scraper.py canonicalises team names at insert via
`normalize_team_name()`, so this should be a one-time cleanup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d2e9f0c1a6'
down_revision: Union[str, None] = 'a3c1d8e2f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_HOCKEY_ACRONYMS = {'AA', 'AAA', 'HADP', 'NBC', 'BC'}


def _normalize(name: str) -> str:
    """Mirror of utilities.utils.normalize_team_name — duplicated here so the
    migration is self-contained and doesn't depend on the rest of the
    codebase being importable at migration time."""
    if not name:
        return name
    name = name.strip()
    if any(c.islower() for c in name):
        return name
    return ' '.join(
        word
        if (any(c.isdigit() for c in word) or word.upper() in _HOCKEY_ACRONYMS)
        else word.title()
        for word in name.split()
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ---- Step 1: merge case-variant duplicate teams -----------------------
    groups = conn.execute(
        sa.text(
            """
            SELECT LOWER(TRIM(name)) AS key
            FROM teams
            GROUP BY LOWER(TRIM(name))
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    print(f"  normalize_team_names: {len(groups)} case-duplicate team group(s)")

    total_dropped = 0
    total_repointed = 0
    total_deleted = 0

    for group in groups:
        candidates = conn.execute(
            sa.text(
                """
                SELECT t.id, t.name, COUNT(st.id) AS standings_count
                FROM teams t
                LEFT JOIN standings st ON st.team_id = t.id
                WHERE LOWER(TRIM(t.name)) = :key
                GROUP BY t.id, t.name
                """
            ),
            {'key': group.key},
        ).fetchall()

        # Winner: prefer the row whose name is NOT all-uppercase (the
        # mixed-case variant), then most standings, then lowest id for
        # determinism.
        def rank(row):
            is_mixed_case = any(c.islower() for c in row.name)
            return (1 if is_mixed_case else 0, row.standings_count, -row.id)

        ranked = sorted(candidates, key=rank, reverse=True)
        winner = ranked[0]
        losers = ranked[1:]

        for loser in losers:
            dropped = conn.execute(
                sa.text(
                    """
                    DELETE FROM standings
                    WHERE team_id = :loser_id
                      AND (season_id, league_id) IN (
                          SELECT season_id, league_id
                          FROM standings
                          WHERE team_id = :winner_id
                      )
                    """
                ),
                {'loser_id': loser.id, 'winner_id': winner.id},
            ).rowcount or 0
            total_dropped += dropped

            repointed = conn.execute(
                sa.text(
                    """
                    UPDATE standings
                    SET team_id = :winner_id
                    WHERE team_id = :loser_id
                    """
                ),
                {'loser_id': loser.id, 'winner_id': winner.id},
            ).rowcount or 0
            total_repointed += repointed

            conn.execute(
                sa.text("DELETE FROM teams WHERE id = :loser_id"),
                {'loser_id': loser.id},
            )
            total_deleted += 1

    print(
        f"  normalize_team_names: dropped {total_dropped} duplicate standings, "
        f"repointed {total_repointed}, deleted {total_deleted} loser team rows"
    )

    # ---- Step 2: normalise remaining all-caps team names ------------------
    # After step 1 there are no LOWER(TRIM(name)) collisions, so renaming
    # an all-caps row to its Title-Case form is safe (no constraint conflict
    # on `teams.name`).
    rows = conn.execute(
        sa.text(
            """
            SELECT id, name FROM teams
            WHERE name = UPPER(name) AND name ~ '[A-Z]{2,}'
            """
        )
    ).fetchall()

    renamed = 0
    for row in rows:
        new_name = _normalize(row.name)
        if new_name != row.name:
            conn.execute(
                sa.text("UPDATE teams SET name = :new WHERE id = :id"),
                {'new': new_name, 'id': row.id},
            )
            renamed += 1

    print(f"  normalize_team_names: renamed {renamed} all-caps team row(s) to mixed case")


def downgrade() -> None:
    # We can't recreate the deleted duplicate team rows, and the rename step
    # is lossy too (we don't track prior casing). This migration is one-way.
    pass
