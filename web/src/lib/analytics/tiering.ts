export type TierInfo = {
  tier: number | 'AA' | null;
  stream: 'BC' | 'NBC';
};

export function parseTierInfo(leagueName: string): TierInfo {
  const upper = leagueName.toUpperCase();

  const stream: 'BC' | 'NBC' =
    upper.includes('NBC') ||
    upper.includes('NON-BODY CHECKING') ||
    upper.includes('NON BODY CHECKING')
      ? 'NBC'
      : 'BC';

  if (upper.includes('AA') || upper.includes('HADP')) {
    return { tier: 'AA', stream };
  }

  let tier: number | null = null;
  const tierMatch = upper.match(/TIER\s+(\d+)/);
  if (tierMatch) {
    tier = parseInt(tierMatch[1], 10);
  } else {
    const nbcMatch = upper.match(/NBC\s+(\d+)/);
    if (nbcMatch) tier = parseInt(nbcMatch[1], 10);
  }

  return { tier, stream };
}

export type TierLabel = 'AA' | 'HADP' | '1' | '2' | '3' | '4' | '5' | '6' | 'Other';

export function extractTierLabel(leagueName: string): TierLabel {
  const info = parseTierInfo(leagueName);
  const upper = (leagueName || '').toUpperCase();
  if (info.tier === 'AA') return upper.includes('HADP') ? 'HADP' : 'AA';
  if (typeof info.tier === 'number') return String(info.tier) as TierLabel;
  return 'Other';
}

export const TIER_ORDER: TierLabel[] = ['AA', 'HADP', '1', '2', '3', '4', '5', '6', 'Other'];
