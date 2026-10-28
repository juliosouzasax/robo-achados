// Proxy do painel: busca os dados no robô (Supabase) com a chave guardada no Vercel.
// A chave nunca vai para o navegador.
const ROBO_URL = process.env.ROBO_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co/functions/v1/robo";

export default async function handler(req, res) {
  try {
    const r = await fetch(`${ROBO_URL}?acao=painel`, {
      headers: { Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}` },
    });
    const j = await r.json();
    res.setHeader("Cache-Control", "s-maxage=120, stale-while-revalidate=600");
    res.status(r.ok ? 200 : 502).json(j);
  } catch (e) {
    res.status(502).json({ erro: "Não consegui falar com o robô: " + String(e) });
  }
}
