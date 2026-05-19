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
import type { LeagueIndexEntry } from '@/lib/analytics/data';

type Props = {
  entries: LeagueIndexEntry[];
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
  group: {
    display: 'flex',
    flexDirection: 'column',
    gap: tokens.spacingVerticalM,
  },
  groupHead: {
    display: 'flex',
    alignItems: 'baseline',
    gap: tokens.spacingHorizontalS,
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

  // Group by season, then sort leagues within a season by name.
  const groups = useMemo(() => {
    const map = new Map<string, LeagueIndexEntry[]>();
    for (const e of filtered) {
      const arr = map.get(e.season) ?? [];
      arr.push(e);
      map.set(e.season, arr);
    }
    for (const arr of map.values()) {
      arr.sort((a, b) => a.league.localeCompare(b.league));
    }
    return Array.from(map.entries()).sort((a, b) => b[0].localeCompare(a[0]));
  }, [filtered]);

  return (
    <div className={s.shell}>
      <TopBar active="leagues" lastUpdated={lastUpdated} />
      <main className={s.main}>
        <div className={s.header}>
          <Title2 as="h1">Leagues</Title2>
          <Body1 style={{ color: tokens.colorNeutralForeground2 }}>
            Browse every season + league combination that has standings. Click through for
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

        {groups.length === 0 ? (
          <div className={s.empty}>
            <Body1>No leagues match the current filter.</Body1>
          </div>
        ) : (
          groups.map(([sn, items]) => (
            <section key={sn} className={s.group}>
              <div className={s.groupHead}>
                <Subtitle1 as="h2">{sn}</Subtitle1>
                <Caption1 className={s.cardMeta}>
                  {items.length} league{items.length === 1 ? '' : 's'}
                </Caption1>
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
                      <Badge appearance="tint" color="brand">{e.ageCategory}</Badge>
                      <Badge appearance="tint" color="informative">{e.tier}</Badge>
                      <Badge appearance="tint" color="subtle">{e.type}</Badge>
                    </div>
                    <Caption1 className={s.cardMeta}>
                      {e.teamCount} team{e.teamCount === 1 ? '' : 's'} · {e.stream}
                    </Caption1>
                  </Link>
                ))}
              </div>
            </section>
          ))
        )}
      </main>
    </div>
  );
}
