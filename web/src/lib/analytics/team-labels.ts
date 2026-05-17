import { extractTierLabel, parseTierInfo } from './tiering';

const TEAM_COLOR_TOKENS = new Set([
  'red', 'blue', 'white', 'black', 'gold', 'silver', 'green', 'yellow',
  'grey', 'gray', 'orange', 'teal', 'navy', 'maroon', 'purple', 'pink',
  'lime', 'cyan', 'magenta', 'brown', 'beige', 'royal', 'sky',
]);

function titleCase(s: string) {
  return s.length ? s[0].toUpperCase() + s.slice(1).toLowerCase() : s;
}

export function parseTeamDifferentiator(teamName: string): { number: number | null; color: string | null } {
  const tokens = (teamName || '').split(/\s+/).filter(Boolean);
  let color: string | null = null;
  if (tokens.length && TEAM_COLOR_TOKENS.has(tokens[tokens.length - 1].toLowerCase())) {
    color = titleCase(tokens.pop()!);
  }
  let number: number | null = null;
  if (tokens.length && /^\d+$/.test(tokens[tokens.length - 1])) {
    number = parseInt(tokens.pop()!, 10);
  }
  return { number, color };
}

export function standardizeTeamLabel(
  teamName: string,
  leagueName: string,
  community: string | null,
): string {
  const ageMatch = (leagueName || '').match(/U\d{1,2}/i);
  const age = ageMatch ? ageMatch[0].toUpperCase() : '';

  const info = parseTierInfo(leagueName || '');
  const tierLabel = extractTierLabel(leagueName || '');
  let tierStr = '';
  if (tierLabel === 'AA' || tierLabel === 'HADP') {
    tierStr = tierLabel;
  } else if (/^\d+$/.test(tierLabel)) {
    tierStr = `Tier ${tierLabel}`;
    if (info.stream === 'NBC') tierStr += ' NBC';
  }

  const { number, color } = parseTeamDifferentiator(teamName);
  const parts = [community || '', age, tierStr];
  if (number !== null) parts.push(`#${number}`);
  if (color) parts.push(color);
  return parts.filter(Boolean).join(' ');
}
