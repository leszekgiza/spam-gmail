import { NextRequest, NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';

function getSQL() {
  return neon(process.env.DATABASE_URL!);
}

export async function GET() {
  const sql = getSQL();

  const decisions = await sql`
    SELECT r.id, r.sender_domain, r.subject, r.snippet, r.received_at,
           f.user_label, f.source, f.created_at as decided_at
    FROM feedback f
    JOIN raw_emails r ON r.id = f.email_id
    WHERE f.source LIKE 'auto_clean:%'
      AND f.created_at > NOW() - INTERVAL '7 days'
    ORDER BY f.created_at DESC
    LIMIT 100
  `;

  const stats = await sql`
    SELECT user_label, COUNT(*) as cnt
    FROM feedback
    WHERE source LIKE 'auto_clean:%'
      AND created_at > NOW() - INTERVAL '24 hours'
    GROUP BY user_label
  `;

  return NextResponse.json({ decisions, stats });
}

export async function POST(req: NextRequest) {
  const sql = getSQL();
  const body = await req.json();
  const { action, emailIds } = body as { action: 'confirm' | 'restore'; emailIds: string[] };

  if (!emailIds?.length) {
    return NextResponse.json({ error: 'No email IDs' }, { status: 400 });
  }

  if (action === 'restore') {
    for (const id of emailIds) {
      await sql`
        UPDATE feedback SET user_label = 'keep', source = 'user_restore', created_at = NOW()
        WHERE email_id = ${id}
      `;
    }
    return NextResponse.json({ restored: emailIds.length });
  }

  if (action === 'confirm') {
    return NextResponse.json({ confirmed: emailIds.length });
  }

  return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
}
