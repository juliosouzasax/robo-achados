// Conectar o canal do YouTube ao robô.
// 1) /api/youtube?k=CONVITE  -> manda para a tela de permissão do Google
// 2) o Google volta para /api/youtube?code=...&state=...  -> o robô guarda o acesso
const ROBO_URL = process.env.ROBO_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co/functions/v1/robo";

async function robo(params) {
  const r = await fetch(`${ROBO_URL}?${new URLSearchParams(params)}`, {
    headers: { Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}` },
  });
  return r.json();
}

function pagina(res, titulo, texto, ok) {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.status(200).send(`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${titulo}</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0a0b;color:#f4efe4;font-family:system-ui,sans-serif;padding:24px}
.c{max-width:460px;border:1px solid rgba(232,182,76,.35);border-radius:18px;padding:28px;background:#141416;text-align:center}
h1{font-size:1.35rem;margin:0 0 10px;color:${ok ? "#f7d98b" : "#ff8a87"}}p{color:#a29c90;line-height:1.5;margin:0}</style></head>
<body><div class="c"><h1>${titulo}</h1><p>${texto}</p></div></body></html>`);
}

export default async function handler(req, res) {
  const { code, state, error, k } = req.query;
  try {
    if (error) return pagina(res, "Conexão cancelada", "O Google não liberou o acesso. Pode tentar de novo pelo mesmo link.", false);
    if (code) {
      const r = await robo({ acao: "youtube_callback", code, state: state || "" });
      return r.ok
        ? pagina(res, "YouTube conectado ✅", "Pronto! A partir do próximo Reel, o robô envia o mesmo vídeo como Short para o canal Achados Decoded. Pode fechar esta página.", true)
        : pagina(res, "Não deu certo", String(r.erro || "Erro desconhecido"), false);
    }
    const r = await robo({ acao: "youtube_url", k: k || "" });
    if (!r.url) return pagina(res, "Link inválido", "Este link de conexão não é válido.", false);
    res.setHeader("Cache-Control", "no-store");
    res.redirect(302, r.url);
  } catch (e) {
    pagina(res, "Não deu certo", "Não consegui falar com o robô: " + String(e), false);
  }
}
