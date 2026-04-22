'use client';

import { useEffect, useState, useCallback } from 'react';

interface Decision {
  id: string;
  sender_domain: string;
  subject: string;
  snippet: string;
  received_at: string;
  user_label: string;
  source: string;
  decided_at: string;
}

export default function Home() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/review');
      const data = await res.json();
      setDecisions(data.decisions || []);
    } catch {
      setMessage('Błąd ładowania danych');
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(decisions.map(d => d.id)));
  };

  const selectNone = () => setSelected(new Set());

  const handleAction = async (action: 'confirm' | 'restore') => {
    const ids = Array.from(selected);
    if (!ids.length) { setMessage('Zaznacz maile'); return; }
    setLoading(true);
    try {
      const res = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, emailIds: ids }),
      });
      const data = await res.json();
      if (action === 'restore') {
        setMessage(`Przywrócono ${data.restored} maili do INBOX (false positive → training)`);
      } else {
        setMessage(`Potwierdzono ${data.confirmed} decyzji AI`);
      }
      setSelected(new Set());
      await load();
    } catch {
      setMessage('Błąd akcji');
    }
    setLoading(false);
  };

  const spamCount = decisions.filter(d => d.user_label === 'spam').length;

  const fmtDate = (s: string) => {
    try { return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); }
    catch { return s; }
  };

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ marginBottom: 4 }}>SPAM Gmail — Poranny przegląd</h1>
      <p style={{ color: '#666', marginTop: 0 }}>
        Ostatnie 7 dni: <strong>{spamCount}</strong> maili oznaczonych do usunięcia
      </p>

      {message && (
        <div style={{
          padding: '8px 16px', marginBottom: 16, borderRadius: 6,
          background: message.includes('Błąd') ? '#fee' : '#efe',
          border: `1px solid ${message.includes('Błąd') ? '#fcc' : '#cfc'}`,
        }}>
          {message}
          <button onClick={() => setMessage('')} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={selectAll} style={btnStyle}>Zaznacz wszystko</button>
        <button onClick={selectNone} style={btnStyle}>Odznacz</button>
        <button onClick={() => handleAction('confirm')} style={{ ...btnStyle, background: '#d32f2f', color: '#fff' }} disabled={loading}>
          Potwierdź usunięcie ({selected.size})
        </button>
        <button onClick={() => handleAction('restore')} style={{ ...btnStyle, background: '#1976d2', color: '#fff' }} disabled={loading}>
          Przywróć zaznaczone ({selected.size})
        </button>
      </div>

      {loading ? (
        <p>Ładowanie...</p>
      ) : decisions.length === 0 ? (
        <p style={{ color: '#999', textAlign: 'center', padding: 40 }}>
          Brak decyzji AI z ostatnich 7 dni. Cron odpala się codziennie o 6:00.
        </p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: '#f5f5f5', textAlign: 'left' }}>
              <th style={thStyle}></th>
              <th style={thStyle}>Data</th>
              <th style={thStyle}>Nadawca</th>
              <th style={thStyle}>Temat</th>
              <th style={thStyle}>Reguła</th>
            </tr>
          </thead>
          <tbody>
            {decisions.map(d => (
              <tr
                key={d.id}
                onClick={() => toggle(d.id)}
                style={{
                  cursor: 'pointer',
                  background: selected.has(d.id) ? '#e3f2fd' : 'transparent',
                  borderBottom: '1px solid #eee',
                }}
              >
                <td style={tdStyle}>
                  <input type="checkbox" checked={selected.has(d.id)} readOnly />
                </td>
                <td style={{ ...tdStyle, whiteSpace: 'nowrap', color: '#666', fontSize: 12 }}>
                  {fmtDate(d.received_at)}
                </td>
                <td style={{ ...tdStyle, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {d.sender_domain}
                </td>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 500 }}>{d.subject}</div>
                  <div style={{ color: '#888', fontSize: 12, marginTop: 2 }}>{d.snippet?.slice(0, 100)}</div>
                </td>
                <td style={{ ...tdStyle, fontSize: 11, color: '#999' }}>
                  {d.source?.replace('auto_clean:', '')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

const btnStyle: React.CSSProperties = {
  padding: '6px 14px', borderRadius: 4, border: '1px solid #ccc',
  background: '#fff', cursor: 'pointer', fontSize: 13,
};
const thStyle: React.CSSProperties = { padding: '8px 6px', borderBottom: '2px solid #ddd' };
const tdStyle: React.CSSProperties = { padding: '8px 6px', verticalAlign: 'top' };
