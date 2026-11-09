// Dados do tráfego pago (Meta Ads) do Garimpo, lidos da tabela public.trafego_anuncios do Supabase.
// A chave fica no Vercel; o navegador só recebe a lista.
const BASE = process.env.SUPABASE_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co";

export default async function handler(req, res) {
  try {
    const r = await fetch(`${BASE}/rest/v1/trafego_anuncios?select=*&order=teste.asc,nome.asc&limit=200`, {
      headers: { apikey: process.env.SUPABASE_ANON_KEY, Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}` },
    });
    const j = await r.json();
    res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=300");
    res.status(r.ok ? 200 : 502).json(r.ok ? { anuncios: j } : { erro: "trafego", detalhe: j });
  } catch (e) {
    res.status(502).json({ erro: "Não consegui ler o tráfego: " + String(e) });
  }
}
