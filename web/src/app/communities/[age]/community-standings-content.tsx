'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Badge,
  Body1,
  Caption1,
  Subtitle1,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { People24Regular } from '@fluentui/react-icons';
import { SectionCard } from '@/app/analytics/section-card';
import { TopBar } from '@/components/top-bar';
import type { CommunityAggregateRow } from '@/lib/analytics/data';

const AGES = ['U11', 'U13', 'U15'] as const;

type Props = {
  age: string;
  season: string | null;
  seasons: string[];
  rows: CommunityAggregateRow[];
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
    gap: tokens.spacingVerticalXL,
    width: '100%',
    maxWidth: '1100px',
    margin: '0 auto',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
  },
  ageTabs: {
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
  },
  ageTab: {
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalL}`,
    borderRadius: tokens.borderRadiusMedium,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground2,
    textDecoration: 'none',
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    ':hover': {
      color: tokens.colorBrandForeground1,
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  ageTabActive: {
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
    border: `1px solid ${tokens.colorBrandBackground}`,
    ':hover': {
      backgroundColor: tokens.colorBrandBackgroundHover,
      color: tokens.colorNeutralForegroundOnBrand,
    },
  },
  seasonChips: {
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
    flexWrap: 'wrap',
    alignItems: 'center',
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
  thRight: { textAlign: 'right' },
  td: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalM}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke3}`,
    whiteSpace: 'nowrap',
    color: tokens.colorNeutralForeground1,
  },
  tdRight: { textAlign: 'right', fontVariantNumeric: 'tabular-nums' },
  rank: {
    color: tokens.colorNeutralForeground3,
    fontVariantNumeric: 'tabular-nums',
    width: '36px',
  },
  community: { fontWeight: tokens.fontWeightSemibold },
  diffPos: { color: tokens.colorPaletteGreenForeground1 },
  diffNeg: { color: tokens.colorPaletteRedForeground1 },
  empty: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: tokens.spacingHorizontalXXL,
    textAlign: 'center',
    color: tokens.colorNeutralForeground2,
  },
});

function formatDiff(d: number): string {
  if (d > 0) return `+${d}`;
  return String(d);
}

export function CommunityStandingsContent({ age, season, seasons, rows, lastUpdated }: Props) {
  const s = useStyles();
  const router = useRouter();
  const ageLower = age.toLowerCase();

  const onSeasonClick = (next: string) => {
    router.push(`/communities/${ageLower}?season=${encodeURIComponent(next)}`);
  };

  return (
    <div className={s.shell}>
      <TopBar active="communities" lastUpdated={lastUpdated} />
      <main className={s.main}>
        <div className={s.header}>
          <Title2 as="h1">Community standings — {age}</Title2>
          <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
            Aggregate W / L / GF / GA / Diff per community across every {age} team in the
            regular season. AA / HADP tiers excluded.
          </Body1>
        </div>

        <div className={s.ageTabs}>
          {AGES.map((a) => (
            <Link
              key={a}
              href={`/communities/${a.toLowerCase()}`}
              className={`${s.ageTab} ${a === age ? s.ageTabActive : ''}`}
            >
              {a}
            </Link>
          ))}
        </div>

        {seasons.length > 1 && (
          <div className={s.seasonChips}>
            <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>Season:</Caption1>
            {seasons.map((sn) => (
              <Badge
                key={sn}
                appearance={sn === season ? 'filled' : 'outline'}
                color={sn === season ? 'brand' : 'subtle'}
                onClick={() => onSeasonClick(sn)}
                style={{ cursor: 'pointer' }}
              >
                {sn}
              </Badge>
            ))}
          </div>
        )}

        <SectionCard
          icon={<People24Regular />}
          title={season ? `${season} aggregate` : 'No data yet'}
          description={
            <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
              {rows.length > 0
                ? `${rows.length} communities • sorted by goal differential.`
                : `No ${age} regular-season standings recorded for this season yet.`}
            </Body1>
          }
        >
          {rows.length === 0 ? (
            <div className={s.empty}>
              <Subtitle1>Nothing to show</Subtitle1>
              <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
                Once the scraper records {age} regular-season standings for {season ?? 'a current season'},
                they&apos;ll appear here.
              </Body1>
            </div>
          ) : (
            <div className={s.scroller}>
              <table className={s.table}>
                <thead>
                  <tr>
                    <th className={s.th}>#</th>
                    <th className={s.th}>Community</th>
                    <th className={`${s.th} ${s.thRight}`}>Teams</th>
                    <th className={`${s.th} ${s.thRight}`}>GP</th>
                    <th className={`${s.th} ${s.thRight}`}>W</th>
                    <th className={`${s.th} ${s.thRight}`}>L</th>
                    <th className={`${s.th} ${s.thRight}`}>T</th>
                    <th className={`${s.th} ${s.thRight}`}>GF</th>
                    <th className={`${s.th} ${s.thRight}`}>GA</th>
                    <th className={`${s.th} ${s.thRight}`}>Diff</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => {
                    const diffClass = r.diff > 0 ? s.diffPos : r.diff < 0 ? s.diffNeg : '';
                    return (
                      <tr key={r.community}>
                        <td className={`${s.td} ${s.rank}`}>{i + 1}</td>
                        <td className={`${s.td} ${s.community}`}>{r.community}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.teamCount}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.gp}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.w}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.l}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.t}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.gf}</td>
                        <td className={`${s.td} ${s.tdRight}`}>{r.ga}</td>
                        <td className={`${s.td} ${s.tdRight} ${diffClass}`}>{formatDiff(r.diff)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </main>
    </div>
  );
}
