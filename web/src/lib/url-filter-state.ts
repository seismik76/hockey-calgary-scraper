'use client';

import { useCallback, useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

/**
 * URL-as-source-of-truth filter state.
 *
 * The URL is the canonical place for filter state — links are shareable, the
 * browser back/forward buttons restore prior views for free, and the React
 * state is just a memoised view of `useSearchParams()`. Setting state writes
 * to the URL via `router.replace` (not `push`) so filter tweaks don't pile
 * onto the history stack.
 *
 * To keep URLs short, the encoder is expected to omit any field that equals
 * its default — a fresh page load with no query string still decodes to the
 * full default state.
 */
export function useUrlFilterState<TState>(
  defaults: TState,
  encode: (state: TState, defaults: TState) => URLSearchParams,
  decode: (params: URLSearchParams, defaults: TState) => TState,
): readonly [TState, (next: TState) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const state = useMemo(
    () => decode(new URLSearchParams(searchParams.toString()), defaults),
    [searchParams, decode, defaults],
  );

  const setState = useCallback(
    (next: TState) => {
      const params = encode(next, defaults);
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, encode, defaults],
  );

  return [state, setState] as const;
}

// Shared codec helpers — every page's encode/decode reaches for these.

export function sameArr<T>(a: readonly T[], b: readonly T[]): boolean {
  return a.length === b.length && a.every((x, i) => x === b[i]);
}

/** Encode a string array as a comma-separated value, omitted entirely when it
 *  matches the default. */
export function putArrayIfChanged(
  params: URLSearchParams,
  key: string,
  value: readonly string[],
  defaultValue: readonly string[],
) {
  if (!sameArr(value, defaultValue)) {
    params.set(key, value.join(','));
  }
}

/** Decode a comma-separated value back to an array, falling back to the
 *  default when the key is absent. */
export function getArray(
  params: URLSearchParams,
  key: string,
  defaultValue: readonly string[],
): string[] {
  const raw = params.get(key);
  if (raw === null) return [...defaultValue];
  // Treat an explicit empty string as an empty selection (user cleared the
  // filter), not as "fall back to default."
  return raw === '' ? [] : raw.split(',').filter(Boolean);
}
