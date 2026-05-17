'use client';

import {
  Button,
  Menu,
  MenuItem,
  MenuList,
  MenuPopover,
  MenuTrigger,
  Tooltip,
} from '@fluentui/react-components';
import { ArrowDownload20Regular } from '@fluentui/react-icons';
import type { StandingRow } from '@/lib/analytics/data';

const CSV_COLUMNS: { key: keyof StandingRow; header: string }[] = [
  { key: 'teamLabel', header: 'Team Label' },
  { key: 'community', header: 'Community' },
  { key: 'season', header: 'Season' },
  { key: 'ageCategory', header: 'Age Category' },
  { key: 'tier', header: 'Tier' },
  { key: 'type', header: 'Type' },
  { key: 'gp', header: 'GP' },
  { key: 'w', header: 'W' },
  { key: 'l', header: 'L' },
  { key: 't', header: 'T' },
  { key: 'pts', header: 'PTS' },
  { key: 'gf', header: 'GF' },
  { key: 'ga', header: 'GA' },
  { key: 'diff', header: 'Diff' },
  { key: 'winPct', header: 'Win %' },
  { key: 'pointsPct', header: 'Points %' },
  { key: 'goalDiffPerGame', header: 'Goal Diff/Game' },
  { key: 'team', header: 'Team' },
  { key: 'league', header: 'League' },
  { key: 'stream', header: 'Stream' },
  { key: 'source', header: 'Source' },
];

function escapeCell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function buildCsv(rows: StandingRow[]): string {
  const header = CSV_COLUMNS.map((c) => c.header).join(',');
  const body = rows
    .map((r) => CSV_COLUMNS.map((c) => escapeCell(r[c.key])).join(','))
    .join('\n');
  return `${header}\n${body}\n`;
}

function download(rows: StandingRow[], filename: string) {
  const blob = new Blob([buildCsv(rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function CsvButton({
  all,
  filtered,
}: {
  all: StandingRow[];
  filtered: StandingRow[];
}) {
  return (
    <Menu>
      <MenuTrigger disableButtonEnhancement>
        <Tooltip content="Export to CSV" relationship="label">
          <Button
            appearance="subtle"
            icon={<ArrowDownload20Regular />}
            aria-label="Export to CSV"
          />
        </Tooltip>
      </MenuTrigger>
      <MenuPopover>
        <MenuList>
          <MenuItem
            onClick={() => download(filtered, 'hockey_calgary_filtered.csv')}
            disabled={filtered.length === 0}
          >
            Filtered view ({filtered.length.toLocaleString()} rows)
          </MenuItem>
          <MenuItem onClick={() => download(all, 'hockey_calgary_all.csv')}>
            All rows ({all.length.toLocaleString()})
          </MenuItem>
        </MenuList>
      </MenuPopover>
    </Menu>
  );
}
