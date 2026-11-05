// Gerador de links de afiliado (página /link). Repassa para o robô no Supabase.
const ROBO_URL = process.env.ROBO_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co/functions/v1/robo";

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const { k = "", url = "", historico } = req.query;
  const params = historico ? { acao: "gerador_historico", k } : { acao: "gerar_link", k, url };
  try {
    const r = await fetch(`${ROBO_URL}?${new URLSearchParams(params)}`, {
      headers: { Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}` },
    });
    res.status(200).json(await r.json());
  } catch (e) {
    res.status(200).json({ erro: "Não consegui falar com o robô agora. Tente de novo em instantes." });
  }
}
