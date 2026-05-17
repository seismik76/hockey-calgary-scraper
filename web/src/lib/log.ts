import 'server-only';

// One JSON line per log entry on stdout. Render's log viewer is fine with
// plain text, but a stable shape makes the logs grep-friendly today and
// directly ingestable by Logtail / Datadog / etc. if we ever ship them off.
//
// Fields:
//   t      ISO-8601 timestamp (UTC)
//   level  'info' | 'warn' | 'error'
//   event  dot-separated event key, e.g. "scraper.run.spawned"
//   ...    everything else: free-form structured fields

type Level = 'info' | 'warn' | 'error';

type Fields = Record<string, unknown>;

function emit(level: Level, event: string, fields?: Fields) {
  const line = JSON.stringify({
    t: new Date().toISOString(),
    level,
    event,
    ...fields,
  });
  // Route warns/errors to stderr so Render's log filtering catches them.
  if (level === 'error' || level === 'warn') {
    process.stderr.write(line + '\n');
  } else {
    process.stdout.write(line + '\n');
  }
}

export const log = {
  info: (event: string, fields?: Fields) => emit('info', event, fields),
  warn: (event: string, fields?: Fields) => emit('warn', event, fields),
  error: (event: string, fields?: Fields) => emit('error', event, fields),
};

/** Pull a recognisable error shape out of an unknown caught value. */
export function errorFields(e: unknown): Fields {
  if (e instanceof Error) {
    return { error: e.message, errorName: e.name };
  }
  return { error: String(e) };
}
