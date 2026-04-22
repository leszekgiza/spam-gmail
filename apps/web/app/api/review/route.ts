import { NextRequest, NextResponse } from 'next/server';

const DB_URL = process.env.DATABASE_URL!;

async function query(sql: string, params: unknown[] = []) {
  // Use pg-compatible HTTP driver via Neon serverless
  const { neon } = await import('@neondatabase/serverless');
  const sql_fn = neon(DB_URL);
  return sql_fn(sql, params);
}

export async function GET() {
  // Ostatnie decyzje purge crona (ostatnie 24h)
  const decisions = await query(`
    SELECT r.id, r.sender_domain, r.subject, r.snippet, r.received_at,
           f.user_label, f.source, f.created_at as decided_at
    FROM feedback f
    JOIN raw_emails r ON r.id = f.email_id
    WHERE f.source LIKE 'auto_clean:%'
      AND f.created_at > NOW() - INTERVAL '7 days'
    ORDER BY f.created_at DESC
    LIMIT 100
  `);

  // Statystyki z ostatniego dry-run (z audit_log jeśli jest)
  const stats = await query(`
    SELECT user_label, COUNT(*) as cnt
    FROM feedback
    WHERE source LIKE 'auto_clean:%'
      AND created_at > NOW() - INTERVAL '24 hours'
    GROUP BY user_label
  `);

  return NextResponse.json({ decisions, stats });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { action, emailIds } = body as { action: 'confirm' | 'restore'; emailIds: string[] };

  if (!emailIds?.length) {
    return NextResponse.json({ error: 'No email IDs' }, { status: 400 });
  }

  if (action === 'restore') {
    // Zmień feedback na keep + oznacz jako false positive
    for (const id of emailIds) {
      await query(
        `UPDATE feedback SET user_label = 'keep', source = 'user_restore', created_at = NOW()
         WHERE email_id = $1`,
        [id]
      );
    }
    return NextResponse.json({ restored: emailIds.length });
  }

  if (action === 'confirm') {
    // User potwierdził — feedback stays as spam
    return NextResponse.json({ confirmed: emailIds.length });
  }

  return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
}
