// Despesas do Garimpo (tráfego pago etc.), lidas da tabela public.despesas do Supabase.
// A chave fica no Vercel; o navegador só recebe a lista.
const BASE = process.env.SUPABASE_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co";

export default async function handler(req, res) {
  try {
    const r = await fetch(`${BASE}/rest/v1/despesas?select=id,data,valor,categoria,descricao&order=data.desc&limit=500`, {
      headers: { apikey: process.env.SUPABASE_ANON_KEY, Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}` },
    });
    const j = await r.json();
    res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=300");
    res.status(r.ok ? 200 : 502).json(r.ok ? { despesas: j } : { erro: "despesas", detalhe: j });
  } catch (e) {
    res.status(502).json({ erro: "Não consegui ler as despesas: " + String(e) });
  }
}
