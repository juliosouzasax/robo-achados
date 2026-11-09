// Função "capa": gera a primeira capa do carrossel (imagem absurda + gancho) com a OpenAI.
// Entrada (POST JSON): { gancho: string, destaque?: string, cena: string }
// Cabeçalho: x-convite = valor de config.yt_convite
// Saída: { url } (imagem salva no bucket público "capas")
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const json = (o: unknown, s = 200) =>
  new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json" } });

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ erro: "use POST" }, 405);
  const { data: c } = await db.from("config").select("valor").eq("chave", "yt_convite").maybeSingle();
  if (!c?.valor || req.headers.get("x-convite") !== c.valor) return json({ erro: "convite inválido" }, 401);

  const b = await req.json().catch(() => ({}));
  const gancho = String(b.gancho ?? "").slice(0, 160);
  const destaque = String(b.destaque ?? "").slice(0, 40);
  const cena = String(b.cena ?? "").slice(0, 400);
  if (!gancho || !cena) return json({ erro: "precisa de gancho e cena" }, 400);

  const prompt =
    `Capa vertical de carrossel de Instagram, fotografia hiper-realista de celular, iluminação natural. ` +
    `Cena absurda e impossível, que chama atenção: ${cena}. ` +
    `A imagem ocupa a tela toda, com a parte de baixo mais escura para o texto. ` +
    `Sobre a metade inferior, escreva EXATAMENTE este texto em português do Brasil, em fonte grossa e arredondada, ` +
    `branca com contorno preto, centralizado, em até 3 linhas: "${gancho}". ` +
    (destaque ? `A palavra "${destaque}" fica sobre uma faixa laranja. ` : "") +
    `Um traço branco desenhado à mão embaixo do texto e uma seta branca desenhada no canto superior esquerdo. ` +
    `Sem logotipos, sem marca d'água, sem outros textos.`;

  const r = await fetch("https://api.openai.com/v1/images/generations", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${Deno.env.get("OPENAI_API_KEY")}` },
    body: JSON.stringify({ model: "gpt-image-1", prompt, size: "1024x1536", quality: "medium", n: 1 }),
  });
  const o = await r.json();
  if (!r.ok || !o.data?.[0]?.b64_json) return json({ erro: "openai", detalhe: o.error?.message ?? o }, 502);

  const bin = Uint8Array.from(atob(o.data[0].b64_json), (ch) => ch.charCodeAt(0));
  const nome = `capa-${Date.now()}.png`;
  const up = await db.storage.from("capas").upload(nome, bin, { contentType: "image/png" });
  if (up.error) return json({ erro: "storage", detalhe: up.error.message }, 500);
  const { data: pub } = db.storage.from("capas").getPublicUrl(nome);
  return json({ url: pub.publicUrl });
});
