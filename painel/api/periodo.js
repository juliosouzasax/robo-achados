// Proxy do painel: métricas do Instagram para um período escolhido (de/ate = AAAA-MM-DD).
const ROBO_URL = process.env.ROBO_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co/functions/v1/robo";
const DATA = /^\d{4}-\d{2}-\d{2}$/;

export default async function handler(req, res) {
  const { de, ate } = req.query || {};
  if (!DATA.test(de || "") || !DATA.test(ate || "")) return res.status(400).json({ erro: "use ?de=AAAA-MM-DD&ate=AAAA-MM-DD" });
  try {
    const r = await fetch(`${ROBO_URL}?acao=painel_periodo&de=${de}&ate=${ate}`, {
      headers: { Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}` },
    });
    const j = await r.json();
    res.setHeader("Cache-Control", "s-maxage=120, stale-while-revalidate=600");
    res.status(r.ok ? 200 : 502).json(j);
  } catch (e) {
    res.status(502).json({ erro: "Não consegui falar com o robô: " + String(e) });
  }
}
