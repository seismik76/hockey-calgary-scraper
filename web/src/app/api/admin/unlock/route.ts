import { NextResponse } from 'next/server';
import { adminEnabled, checkPassword, setAdminCookie } from '@/lib/auth';
import { log } from '@/lib/log';

export async function POST(req: Request) {
  if (!adminEnabled()) {
    return NextResponse.json({ error: 'admin disabled' }, { status: 404 });
  }
  let body: { password?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid body' }, { status: 400 });
  }
  if (!checkPassword(body.password ?? '')) {
    log.warn('admin.unlock.bad_password');
    return NextResponse.json({ error: 'wrong password' }, { status: 401 });
  }
  await setAdminCookie();
  log.info('admin.unlock.ok');
  return NextResponse.json({ ok: true });
}
