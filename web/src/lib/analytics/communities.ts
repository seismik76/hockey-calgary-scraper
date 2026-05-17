// Stable color per community — same color in every chart on every page. Anything
// not in the map falls back to a default Recharts color.
export const COMMUNITY_COLORS: Record<string, string> = {
  'Bow River': '#1f77b4', // blue
  'Bow Valley': '#2ca02c', // green
  Glenlake: '#d62728', // red
  Knights: '#9467bd', // purple
  McKnight: '#ff7f0e', // orange
  'North West': '#17becf', // cyan
  Raiders: '#8c564b', // brown
  Southwest: '#e377c2', // pink
  Springbank: '#bcbd22', // olive
  'Trails West': '#7f7f7f', // grey
  Wolverines: '#aec7e8', // light blue
};

export const FALLBACK_COLORS = [
  '#4f6d7a',
  '#c0a8c0',
  '#86a59c',
  '#d4a373',
  '#b08968',
  '#6d6875',
];

export function communityColor(community: string, fallbackIndex = 0): string {
  return (
    COMMUNITY_COLORS[community] ??
    FALLBACK_COLORS[fallbackIndex % FALLBACK_COLORS.length]
  );
}

export const NORTH_COMMUNITIES = ['Springbank', 'North West', 'Bow River', 'McKnight', 'Raiders'];
export const SOUTH_COMMUNITIES = ['Trails West', 'Glenlake', 'Bow Valley', 'Knights', 'Southwest', 'Wolverines'];

export type Division = 'All' | 'North' | 'South';

export function filterByDivision(communities: string[], division: Division): string[] {
  if (division === 'North') return communities.filter((c) => NORTH_COMMUNITIES.includes(c));
  if (division === 'South') return communities.filter((c) => SOUTH_COMMUNITIES.includes(c));
  return communities;
}
