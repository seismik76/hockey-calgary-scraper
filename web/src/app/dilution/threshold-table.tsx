'use client';

import { Body1, makeStyles, tokens } from '@fluentui/react-components';
import { Settings24Regular } from '@fluentui/react-icons';
import { SectionCard } from '@/app/analytics/section-card';
import type { ThresholdEntry } from '@/lib/analytics/dilution';

const useStyles = makeStyles({
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
  td: {
    padding: `${tokens.spacingVerticalM} ${tokens.spacingHorizontalM}`,
    borderBottom: `1px solid ${tokens.colorNeutralStroke3}`,
    color: tokens.colorNeutralForeground1,
  },
  tdRight: {
    textAlign: 'right',
    fontVariantNumeric: 'tabular-nums',
    whiteSpace: 'nowrap',
  },
  outliers: {
    color: tokens.colorNeutralForeground2,
    fontSize: '12px',
  },
});

export function ThresholdTable({ entries }: { entries: ThresholdEntry[] }) {
  const s = useStyles();
  if (entries.length === 0) {
    return (
      <SectionCard
        icon={<Settings24Regular />}
        title="Inferred thresholds"
        description="No threshold data available for the current filters."
      >
        <Body1>Need at least one community with 2+ Tier 1 teams to infer a threshold.</Body1>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      icon={<Settings24Regular />}
      title="Inferred thresholds"
      description="Team-count threshold above which an association is expected to field 2+ Tier 1 teams. Inferred per Season × Age from the full community pool."
    >
      <div className={s.scroller}>
        <table className={s.table}>
          <thead>
            <tr>
              <th className={s.th}>Season</th>
              <th className={s.th}>Age</th>
              <th className={s.th} style={{ textAlign: 'right' }}>
                Threshold
              </th>
              <th className={s.th}>Outliers</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={`${e.season}-${e.ageCategory}`}>
                <td className={s.td}>{e.season}</td>
                <td className={s.td}>{e.ageCategory}</td>
                <td className={`${s.td} ${s.tdRight}`}>
                  {e.threshold === 999 ? '—' : e.threshold}
                </td>
                <td className={`${s.td} ${s.outliers}`}>
                  {e.outliers.length === 0 ? '—' : e.outliers.join(', ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
