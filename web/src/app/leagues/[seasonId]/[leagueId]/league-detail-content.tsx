'use client';

import React from 'react';
import Link from 'next/link';
import {
  Badge,
  Body1,
  Caption1,
  Link as FluentLink,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import {
  ArrowLeft20Regular,
  CalendarLtr24Regular,
  Open20Regular,
  Trophy24Regular,
} from '@fluentui/react-icons';
import { SectionCard } from '@/app/analytics/section-card';
import { TopBar } from '@/components/top-bar';
import type { LeagueDetail, LeagueGame, StandingRow } from '@/lib/analytics/data';

type SerializedGame = Omit<LeagueGame, 'playedAt'> & { playedAt: string | null };

type Props = {
  detail: LeagueDetail;
  games: SerializedGame[];
  lastUpdated: { finishedAt: Date | null; standingsCount: number | null } | null;
};

const useStyles = makeStyles({
  shell: {
    minHeight: '100vh',
    backgroundColor: tokens.colorNeutralBackground2,
    display: 'flex',
    flexDirection: 'column',
  },
  main: {
    padding: `${tokens.spacingVerticalXXL} ${tokens.spacingHorizontalXXL}`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXXL,
    width: '100%',
    maxWidth: '1100px',
    margin: '0 auto',
    boxSizing: 'border-box',
  },
  back: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalXS,
    color: tokens.colorNeutralForeground2,
    textDecoration: 'none',
    fontSize: '13px',
    width: 'fit-content',
    ':hover': { color: tokens.colorBrandForeground1 },
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
  },
  badges: {
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
    flexWrap: 'wrap',
  },
  summary: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: tokens.spacingHorizontalM,
  },
  stat: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalL}`,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalXXS,
  },
  statLabel: {
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: tokens.colorNeutralForeground3,
  },
  statValue: {
    fontSize: '20px',
    fontWeight: tokens.fontWeightSemibold,
    fontVariantNumeric: 'tabular-nums',
    color: tokens.colorNeutralForeground1,
  },
  scroller: {
    overflowX: 'auto',
    borderRadius: tokens.borderRadiusLarge,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  table: {
    width: '100%',
    borderCollapse: 'separate',
    borderSpacing: 0,
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    fontWeight: tokens.fontWeightSemibold,
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: tokens.colorNeutralForeground3,
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    backgroundColor: tokens.colorNeutralBackground2,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    whiteSpace: 'nowrap',
  },
  thRight: {
    textAlign: 'right',
  },
  td: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalM}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke3}`,
    whiteSpace: 'nowrap',
    color: tokens.colorNeutralForeground1,
  },
  tdRight: {
    textAlign: 'right',
    fontVariantNumeric: 'tabular-nums',
  },
  rank: {
    color: tokens.colorNeutralForeground3,
    fontVariantNumeric: 'tabular-nums',
    width: '36px',
  },
  standingsTeamCell: {
    fontWeight: tokens.fontWeightSemibold,
  },
  diffPos: { color: tokens.colorPaletteGreenForeground1 },
  diffNeg: { color: tokens.colorPaletteRedForeground1 },
  scheduleCard: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: tokens.spacingHorizontalL,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
  },
  resultsTable: {
    width: '100%',
    borderCollapse: 'separate',
    borderSpacing: 0,
    fontSize: '13px',
  },
  dateCell: {
    color: tokens.colorNeutralForeground2,
    fontVariantNumeric: 'tabular-nums',
    whiteSpace: 'nowrap',
  },
  teamCell: {
    color: tokens.colorNeutralForeground1,
  },
  teamWin: {
    fontWeight: tokens.fontWeightSemibold,
  },
  teamLoss: {
    color: tokens.colorNeutralForeground3,
  },
  scoreCell: {
    textAlign: 'center',
    fontVariantNumeric: 'tabular-nums',
    fontWeight: tokens.fontWeightSemibold,
    minWidth: '70px',
  },
  venueCell: {
    color: tokens.colorNeutralForeground3,
    fontSize: '12px',
  },
  typePill: {
    display: 'inline-block',
    fontSize: '10px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    padding: '2px 6px',
    borderRadius: tokens.borderRadiusSmall,
    backgroundColor: tokens.colorNeutralBackground2,
    color: tokens.colorNeutralForeground3,
  },
  groupHeader: {
    backgroundColor: tokens.colorNeutralBackground2,
    color: tokens.colorNeutralForeground3,
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    borderTop: `1px solid ${tokens.colorNeutralStroke3}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke3}`,
  },
  footer: {
    paddingTop: tokens.spacingVerticalL,
    borderTop: `1px solid ${tokens.colorNeutralStroke2}`,
    color: tokens.colorNeutralForeground3,
  },
});

function formatDiff(d: number | null): string {
  if (d == null) return '';
  if (d > 0) return `+${d}`;
  return String(d);
}

function formatGameDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

function formatGameTime(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const h = d.getHours();
  const m = d.getMinutes();
  if (h === 0 && m === 0) return '';
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

function monthKey(iso: string | null): string {
  if (!iso) return 'No date';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

export function LeagueDetailContent({ detail, games, lastUpdated }: Props) {
  const s = useStyles();
  const { season, league, type, stream, ageCategory, tier, sourceUrl, rows } = detail;

  const totals = rows.reduce(
    (acc, r) => {
      acc.gp += r.gp ?? 0;
      acc.gf += r.gf ?? 0;
      acc.ga += r.ga ?? 0;
      return acc;
    },
    { gp: 0, gf: 0, ga: 0 },
  );
  // Each game is counted twice in per-team totals — once per team.
  const gamesPlayed = Math.round(totals.gp / 2);

  return (
    <div className={s.shell}>
      <TopBar active="leagues" lastUpdated={lastUpdated} />
      <main className={s.main}>
        <Link href="/leagues" className={s.back}>
          <ArrowLeft20Regular /> Back to leagues
        </Link>

        <div className={s.header}>
          <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>{season}</Caption1>
          <Title2 as="h1">{league}</Title2>
          <div className={s.badges}>
            <Badge appearance="tint" color="brand">{ageCategory}</Badge>
            <Badge appearance="tint" color="informative">{tier}</Badge>
            <Badge appearance="tint" color="subtle">{type}</Badge>
            <Badge appearance="tint" color="subtle">{stream}</Badge>
          </div>
        </div>

        <div className={s.summary}>
          <div className={s.stat}>
            <span className={s.statLabel}>Teams</span>
            <span className={s.statValue}>{rows.length}</span>
          </div>
          <div className={s.stat}>
            <span className={s.statLabel}>Games played</span>
            <span className={s.statValue}>{gamesPlayed}</span>
          </div>
          <div className={s.stat}>
            <span className={s.statLabel}>Total goals</span>
            <span className={s.statValue}>{totals.gf}</span>
          </div>
          <div className={s.stat}>
            <span className={s.statLabel}>Goals / game</span>
            <span className={s.statValue}>
              {gamesPlayed > 0 ? (totals.gf / gamesPlayed).toFixed(1) : '—'}
            </span>
          </div>
        </div>

        <SectionCard
          icon={<Trophy24Regular />}
          title="Standings"
          description={
            <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
              Sorted by points, then goal differential. Ties broken by goals for.
            </Body1>
          }
        >
          <div className={s.scroller}>
            <table className={s.table}>
              <thead>
                <tr>
                  <th className={s.th}>#</th>
                  <th className={s.th}>Team</th>
                  <th className={s.th}>Community</th>
                  <th className={`${s.th} ${s.thRight}`}>GP</th>
                  <th className={`${s.th} ${s.thRight}`}>W</th>
                  <th className={`${s.th} ${s.thRight}`}>L</th>
                  <th className={`${s.th} ${s.thRight}`}>T</th>
                  <th className={`${s.th} ${s.thRight}`}>PTS</th>
                  <th className={`${s.th} ${s.thRight}`}>GF</th>
                  <th className={`${s.th} ${s.thRight}`}>GA</th>
                  <th className={`${s.th} ${s.thRight}`}>Diff</th>
                  <th className={`${s.th} ${s.thRight}`}>Win %</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <StandingRowCells key={`${r.team}-${i}`} row={r} rank={i + 1} s={s} />
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard
          icon={<CalendarLtr24Regular />}
          title="Schedule of results"
          description={
            <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
              {games.length > 0
                ? `${games.length} completed game${games.length === 1 ? '' : 's'} for this league.`
                : 'No completed games captured for this league yet. The upstream source may not have published scores.'}
              {sourceUrl && (
                <>
                  {' '}
                  <FluentLink
                    href={sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    View upstream <Open20Regular />
                  </FluentLink>
                </>
              )}
            </Body1>
          }
        >
          {games.length > 0 && <ResultsTable games={games} s={s} />}
        </SectionCard>

        <footer className={s.footer}>
          <Caption1>
            Personal-interest project — not an authoritative source. Data scraped from
            Hockey Calgary, RAMP (Alberta One), and TeamLinkt.
          </Caption1>
        </footer>
      </main>
    </div>
  );
}

function ResultsTable({
  games,
  s,
}: {
  games: SerializedGame[];
  s: ReturnType<typeof useStyles>;
}) {
  // Group by month so longer schedules stay scannable.
  const groups: { label: string; items: SerializedGame[] }[] = [];
  let currentLabel = '';
  for (const g of games) {
    const label = monthKey(g.playedAt);
    if (label !== currentLabel) {
      groups.push({ label, items: [] });
      currentLabel = label;
    }
    groups[groups.length - 1].items.push(g);
  }

  return (
    <div className={s.scroller}>
      <table className={s.resultsTable}>
        <thead>
          <tr>
            <th className={s.th}>Date</th>
            <th className={s.th}>Home</th>
            <th className={s.th}>Score</th>
            <th className={s.th}>Visitor</th>
            <th className={s.th}>Venue</th>
            <th className={s.th}>Type</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((grp) => (
            <React.Fragment key={grp.label}>
              <tr>
                <td colSpan={6} className={s.groupHeader}>{grp.label}</td>
              </tr>
              {grp.items.map((g) => {
                const homeWon = g.homeScore > g.awayScore;
                const awayWon = g.awayScore > g.homeScore;
                return (
                  <tr key={g.id}>
                    <td className={`${s.td} ${s.dateCell}`}>
                      <div>{formatGameDate(g.playedAt)}</div>
                      <div style={{ fontSize: '11px', color: 'inherit' }}>
                        {formatGameTime(g.playedAt)}
                      </div>
                    </td>
                    <td className={`${s.td} ${s.teamCell} ${homeWon ? s.teamWin : awayWon ? s.teamLoss : ''}`}>
                      {g.homeTeamLabel}
                    </td>
                    <td className={`${s.td} ${s.scoreCell}`}>
                      {g.homeScore} – {g.awayScore}
                    </td>
                    <td className={`${s.td} ${s.teamCell} ${awayWon ? s.teamWin : homeWon ? s.teamLoss : ''}`}>
                      {g.awayTeamLabel}
                    </td>
                    <td className={`${s.td} ${s.venueCell}`}>{g.venue ?? ''}</td>
                    <td className={s.td}>
                      <span className={s.typePill}>{g.gameType}</span>
                    </td>
                  </tr>
                );
              })}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StandingRowCells({
  row,
  rank,
  s,
}: {
  row: StandingRow;
  rank: number;
  s: ReturnType<typeof useStyles>;
}) {
  const diff = row.diff ?? 0;
  const diffClass = diff > 0 ? s.diffPos : diff < 0 ? s.diffNeg : '';
  return (
    <tr>
      <td className={`${s.td} ${s.rank}`}>{rank}</td>
      <td className={`${s.td} ${s.standingsTeamCell}`}>{row.teamLabel}</td>
      <td className={s.td}>{row.community ?? ''}</td>
      <td className={`${s.td} ${s.tdRight}`}>{row.gp ?? ''}</td>
      <td className={`${s.td} ${s.tdRight}`}>{row.w ?? ''}</td>
      <td className={`${s.td} ${s.tdRight}`}>{row.l ?? ''}</td>
      <td className={`${s.td} ${s.tdRight}`}>{row.t ?? ''}</td>
      <td className={`${s.td} ${s.tdRight}`}>
        <strong>{row.pts ?? ''}</strong>
      </td>
      <td className={`${s.td} ${s.tdRight}`}>{row.gf ?? ''}</td>
      <td className={`${s.td} ${s.tdRight}`}>{row.ga ?? ''}</td>
      <td className={`${s.td} ${s.tdRight} ${diffClass}`}>{formatDiff(row.diff)}</td>
      <td className={`${s.td} ${s.tdRight}`}>
        {(row.winPct * 100).toFixed(1)}%
      </td>
    </tr>
  );
}
