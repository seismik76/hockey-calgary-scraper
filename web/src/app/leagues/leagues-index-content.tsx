'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  Badge,
  Body1,
  Button,
  Caption1,
  Input,
  Subtitle1,
  Title2,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import {
  ArrowRight16Regular,
  DismissCircle20Regular,
  Search20Regular,
} from '@fluentui/react-icons';
import { TopBar } from '@/components/top-bar';
import { TIER_ORDER } from '@/lib/analytics/tiering';
import type { LeagueIndexEntry } from '@/lib/analytics/data';

type Props = {
  entries: LeagueIndexEntry[];
  lastUpdated: { finishedAt: Date | null; standingsCount: number | null } | null;
};

// Display order for age groups. Anything not in the list falls to the bottom
// under "Other" — covers ages we haven't seen + any future U7/U9 additions.
const AGE_ORDER = ['U7', 'U9', 'U11', 'U13', 'U15', 'U16', 'U18', 'Other'];

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
  controls: {
    display: 'flex',
    gap: tokens.spacingHorizontalM,
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  search: {
    flex: '1 1 280px',
    maxWidth: '420px',
  },
  seasonChips: {
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
    flexWrap: 'wrap',
  },
  ageNav: {
    position: 'sticky',
    top: '64px',
    zIndex: 5,
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
    flexWrap: 'wrap',
    padding: `${tokens.spacingVerticalS} ${tokens.spacingHorizontalM}`,
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    boxShadow: tokens.shadow2,
  },
  ageJump: {
    padding: `${tokens.spacingVerticalXS} ${tokens.spacingHorizontalM}`,
    borderRadius: tokens.borderRadiusMedium,
    fontSize: '13px',
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground2,
    textDecoration: 'none',
    backgroundColor: tokens.colorNeutralBackground2,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    ':hover': {
      color: tokens.colorBrandForeground1,
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  ageJumpCount: {
    marginLeft: '4px',
    color: tokens.colorNeutralForeground3,
    fontWeight: tokens.fontWeightRegular,
    fontVariantNumeric: 'tabular-nums',
  },
  ageSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalL,
    scrollMarginTop: '140px',
  },
  ageHead: {
    display: 'flex',
    alignItems: 'baseline',
    gap: tokens.spacingHorizontalS,
    paddingBottom: tokens.spacingVerticalS,
    borderBottom: `2px solid ${tokens.colorNeutralStroke2}`,
  },
  tierGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
  },
  tierHead: {
    display: 'flex',
    alignItems: 'baseline',
    gap: tokens.spacingHorizontalS,
    color: tokens.colorNeutralForeground2,
    fontSize: '13px',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    fontWeight: tokens.fontWeightSemibold,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: tokens.spacingHorizontalM,
  },
  card: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: tokens.spacingHorizontalL,
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalS,
    textDecoration: 'none',
    color: 'inherit',
    transition: 'border-color 0.12s, box-shadow 0.12s',
    ':hover': {
      border: `1px solid ${tokens.colorBrandStroke1}`,
      boxShadow: tokens.shadow4,
    },
  },
  cardTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalXS,
    color: tokens.colorNeutralForeground1,
    fontWeight: tokens.fontWeightSemibold,
  },
  cardBadges: {
    display: 'flex',
    gap: tokens.spacingHorizontalXS,
    flexWrap: 'wrap',
  },
  cardMeta: {
    color: tokens.colorNeutralForeground3,
    fontVariantNumeric: 'tabular-nums',
  },
  empty: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: tokens.borderRadiusLarge,
    padding: tokens.spacingHorizontalXXL,
    textAlign: 'center',
    color: tokens.colorNeutralForeground2,
  },
});

// Pretty-print a tier label for the section heading.
function tierHeading(tier: string): string {
  if (tier === 'AA' || tier === 'HADP') return tier;
  if (/^\d+$/.test(tier)) return `Tier ${tier}`;
  return 'Other';
}

// Pretty-print an age label for the section heading.
function ageHeading(age: string): string {
  return age === 'Other' ? 'Other ages' : age;
}

export function LeagueIndexContent({ entries, lastUpdated }: Props) {
  const s = useStyles();
  const [query, setQuery] = useState('');

  const seasons = useMemo(
    () => Array.from(new Set(entries.map((e) => e.season))).sort().reverse(),
    [entries],
  );
  const [season, setSeason] = useState<string>(() => seasons[0] ?? '');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return entries.filter((e) => {
      if (season && e.season !== season) return false;
      if (!q) return true;
      return (
        e.league.toLowerCase().includes(q) ||
        e.ageCategory.toLowerCase().includes(q) ||
        e.tier.toLowerCase().includes(q) ||
        e.type.toLowerCase().includes(q) ||
        e.stream.toLowerCase().includes(q)
      );
    });
  }, [entries, query, season]);

  // age -> tier -> entries, in display order.
  const ageGroups = useMemo(() => {
    const byAge = new Map<string, Map<string, LeagueIndexEntry[]>>();
    for (const e of filtered) {
      const age = AGE_ORDER.includes(e.ageCategory) ? e.ageCategory : 'Other';
      let byTier = byAge.get(age);
      if (!byTier) {
        byTier = new Map<string, LeagueIndexEntry[]>();
        byAge.set(age, byTier);
      }
      const arr = byTier.get(e.tier) ?? [];
      arr.push(e);
      byTier.set(e.tier, arr);
    }
    // Order tiers within an age, and leagues within a tier.
    const result: { age: string; total: number; tiers: { tier: string; items: LeagueIndexEntry[] }[] }[] = [];
    for (const age of AGE_ORDER) {
      const byTier = byAge.get(age);
      if (!byTier) continue;
      const tiers: { tier: string; items: LeagueIndexEntry[] }[] = [];
      for (const tier of TIER_ORDER) {
        const items = byTier.get(tier);
        if (!items) continue;
        items.sort((a, b) => a.league.localeCompare(b.league));
        tiers.push({ tier, items });
      }
      // Any tier not in TIER_ORDER (defensive) falls under Other at the end.
      for (const [tier, items] of byTier) {
        if (TIER_ORDER.includes(tier as never)) continue;
        items.sort((a, b) => a.league.localeCompare(b.league));
        tiers.push({ tier, items });
      }
      const total = tiers.reduce((n, t) => n + t.items.length, 0);
      result.push({ age, total, tiers });
    }
    return result;
  }, [filtered]);

  return (
    <div className={s.shell}>
      <TopBar active="leagues" lastUpdated={lastUpdated} />
      <main className={s.main}>
        <div className={s.header}>
          <Title2 as="h1">Leagues</Title2>
          <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
            Browse every league with standings, grouped by age and tier. Click through for
            a focused view of one division.
          </Body1>
        </div>

        <div className={s.controls}>
          <div className={s.search}>
            <Input
              placeholder="Filter by name, age, tier, type, stream…"
              value={query}
              contentBefore={<Search20Regular />}
              contentAfter={
                query ? (
                  <Button
                    appearance="transparent"
                    size="small"
                    icon={<DismissCircle20Regular />}
                    onClick={() => setQuery('')}
                    aria-label="Clear search"
                  />
                ) : undefined
              }
              onChange={(_, data) => setQuery(data.value)}
            />
          </div>
          <div className={s.seasonChips}>
            <Badge
              appearance={season === '' ? 'filled' : 'outline'}
              color={season === '' ? 'brand' : 'subtle'}
              onClick={() => setSeason('')}
              style={{ cursor: 'pointer' }}
            >
              All seasons
            </Badge>
            {seasons.map((sn) => (
              <Badge
                key={sn}
                appearance={sn === season ? 'filled' : 'outline'}
                color={sn === season ? 'brand' : 'subtle'}
                onClick={() => setSeason(sn)}
                style={{ cursor: 'pointer' }}
              >
                {sn}
              </Badge>
            ))}
          </div>
        </div>

        {ageGroups.length > 0 && (
          <nav className={s.ageNav} aria-label="Jump to age group">
            {ageGroups.map((g) => (
              <a key={g.age} href={`#age-${g.age}`} className={s.ageJump}>
                {ageHeading(g.age)}
                <span className={s.ageJumpCount}>{g.total}</span>
              </a>
            ))}
          </nav>
        )}

        {ageGroups.length === 0 ? (
          <div className={s.empty}>
            <Body1>No leagues match the current filter.</Body1>
          </div>
        ) : (
          ageGroups.map((g) => (
            <section key={g.age} id={`age-${g.age}`} className={s.ageSection}>
              <div className={s.ageHead}>
                <Subtitle1 as="h2">{ageHeading(g.age)}</Subtitle1>
                <Caption1 className={s.cardMeta}>
                  {g.total} league{g.total === 1 ? '' : 's'}
                </Caption1>
              </div>
              {g.tiers.map(({ tier, items }) => (
                <div key={tier} className={s.tierGroup}>
                  <div className={s.tierHead}>
                    {tierHeading(tier)}
                    <Caption1 className={s.cardMeta}>{items.length}</Caption1>
                  </div>
                  <div className={s.grid}>
                    {items.map((e) => (
                      <Link
                        key={`${e.seasonId}-${e.leagueId}`}
                        href={`/leagues/${e.seasonId}/${e.leagueId}`}
                        className={s.card}
                      >
                        <div className={s.cardTitle}>
                          <span>{e.league}</span>
                          <ArrowRight16Regular />
                        </div>
                        <div className={s.cardBadges}>
                          <Badge appearance="tint" color="subtle">{e.type}</Badge>
                          {season === '' && (
                            <Badge appearance="tint" color="informative">{e.season}</Badge>
                          )}
                        </div>
                        <Caption1 className={s.cardMeta}>
                          {e.teamCount} team{e.teamCount === 1 ? '' : 's'} · {e.stream}
                        </Caption1>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          ))
        )}
      </main>
    </div>
  );
}
