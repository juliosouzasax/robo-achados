// carrossel-auto: monta e posta 1 carrossel por execução, sem intervenção humana.
// POST {modo:"teste"|"publicar"}  (cabeçalho x-convite = config.yt_convite)
// teste = gera as imagens e devolve as URLs, sem postar. publicar = posta no Instagram.
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { Image } from "https://deno.land/x/imagescript@1.3.0/mod.ts";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const IG_USER = "17841417870379395";
const GRUPO = "https://chat.whatsapp.com/ENU15xRGku18sDqfq3YXlt";
const json = (o: unknown, s = 200) =>
  new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json" } });
const OPENAI = Deno.env.get("OPENAI_API_KEY")!;

async function conf(chave: string) {
  const { data } = await db.from("config").select("valor").eq("chave", chave).maybeSingle();
  return data?.valor as string | undefined;
}
const brl = (n: number) => "R$ " + Number(n).toFixed(2).replace(".", ",");

// ---------- 1) gancho + cena absurda (texto) ----------
async function ideia(titulos: string[]) {
  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${OPENAI}` },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: "Você cria capas virais de carrossel de achadinhos da Shopee para o Instagram, em português do Brasil. Responda só JSON." },
        { role: "user", content:
          `Produtos do carrossel: ${titulos.join("; ")}.\n` +
          `Crie: "gancho" (até 70 caracteres, tom de 'achei que era furada/bobeira, mas virou necessidade', sem emoji), ` +
          `"destaque" (1 a 3 palavras do próprio gancho, que ficam numa faixa laranja), ` +
          `"cena" (uma cena absurda e impossível, fotorrealista, de UM objeto do dia a dia ganhando traços de bicho, pessoa ou outra coisa, ligada ao tema dos produtos; até 220 caracteres).\n` +
          `Responda EXATAMENTE neste formato: {"gancho":"...","destaque":"...","cena":"..."}` },
      ],
    }),
  });
  const o = await r.json();
  const j = JSON.parse(o.choices?.[0]?.message?.content ?? "{}");
  if (!j.gancho || !j.cena) throw new Error("ideia: resposta vazia " + JSON.stringify(o).slice(0, 200));
  return { gancho: String(j.gancho).slice(0, 90), destaque: String(j.destaque ?? "").slice(0, 40), cena: String(j.cena).slice(0, 300) };
}

// ---------- 2) capa (OpenAI imagem) ----------
async function gerarCapa(i: { gancho: string; destaque: string; cena: string }) {
  const prompt =
    `Capa vertical de carrossel de Instagram, fotografia hiper-realista de celular, iluminação natural. ` +
    `Cena absurda e impossível, que chama atenção: ${i.cena}. ` +
    `A imagem ocupa a tela toda, com a parte de baixo mais escura para o texto. ` +
    `Sobre a metade inferior, escreva EXATAMENTE este texto em português do Brasil, em fonte grossa e arredondada, ` +
    `branca com contorno preto, centralizado, em até 3 linhas: "${i.gancho}". ` +
    (i.destaque ? `A expressão "${i.destaque}" fica sobre uma faixa laranja. ` : "") +
    `Um traço branco desenhado à mão embaixo do texto e uma seta branca desenhada no canto superior esquerdo. ` +
    `Sem logotipos, sem marca d'água, sem outros textos.`;
  let ultimo = "";
  for (const model of ["gpt-image-1", "gpt-image-1-mini"]) {
    const r = await fetch("https://api.openai.com/v1/images/generations", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${OPENAI}` },
      body: JSON.stringify({ model, prompt, size: "1024x1536", quality: "medium", n: 1 }),
    });
    const o = await r.json();
    if (r.ok && o.data?.[0]?.b64_json) return Uint8Array.from(atob(o.data[0].b64_json), (c) => c.charCodeAt(0));
    ultimo = `${model}: ${o.error?.message ?? JSON.stringify(o).slice(0, 200)}`;
  }
  throw new Error("capa: " + ultimo);
}

// ---------- 3) slides dos produtos ----------
let FONTE: Uint8Array | null = null;
async function fonte() {
  if (!FONTE) {
    const r = await fetch("https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf");
    if (!r.ok) throw new Error("fonte indisponível");
    FONTE = new Uint8Array(await r.arrayBuffer());
  }
  return FONTE;
}
async function linhas(texto: string, tam: number, larg: number, max: number) {
  const f = await fonte();
  const out: string[] = [];
  let atual = "";
  for (const w of texto.split(/\s+/)) {
    const t = atual ? atual + " " + w : w;
    const img = await Image.renderText(f, tam, t, 0x000000ff);
    if (img.width > larg && atual) { out.push(atual); atual = w; } else atual = t;
  }
  if (atual) out.push(atual);
  return out.slice(0, max);
}
async function texto(img: Image, t: string, tam: number, cor: number, x: number, y: number, centro = false, larg = 0) {
  const tx = await Image.renderText(await fonte(), tam, t, cor);
  img.composite(tx, centro ? x + Math.round((larg - tx.width) / 2) : x, y);
}
async function slideProduto(p: any, n: number) {
  const r = await fetch(p.imagem_url, { headers: { accept: "image/jpeg,image/png" } });
  if (!r.ok) throw new Error("foto " + r.status);
  let foto = await Image.decode(new Uint8Array(await r.arrayBuffer()));
  const W = 1080, H = 1350;
  const esc = Math.min(900 / foto.width, 900 / foto.height);
  foto = foto.resize(Math.round(foto.width * esc), Math.round(foto.height * esc));
  const bg = new Image(W, H).fill(0xfff3e8ff);
  bg.composite(new Image(960, 1010).fill(0xffffffff), 60, 60);
  bg.composite(foto, 60 + Math.round((960 - foto.width) / 2), 60 + Math.round((1010 - foto.height) / 2));
  bg.composite(new Image(150, 150).fill(0xff6b2cff), 60, 60);
  await texto(bg, String(n), 110, 0xffffffff, 60, 85, true, 150);
  const tit = await linhas(p.titulo_curto || p.titulo, 52, 940, 2);
  let y = 1090;
  for (const l of tit) { await texto(bg, l, 52, 0x222222ff, 70, y); y += 66; }
  await texto(bg, brl(p.preco), 88, 0xff6b2cff, 70, 1215);
  return await bg.encodeJPEG(88);
}
async function slideFinal(n: string) {
  const W = 1080, H = 1350;
  const bg = new Image(W, H).fill(0xff6b2cff);
  const bloco: [string, number][] = [["Quer os links?", 120], ["Comenta QUERO", 100], ["que eu te mando", 70], ["no seu direct", 70]];
  let y = 360;
  for (const [t, s] of bloco) { await texto(bg, t, s, 0xffffffff, 0, y, true, W); y += s + 50; }
  await texto(bg, `Carrossel ${n}`, 44, 0xfff3e8ff, 0, 1210, true, W);
  return await bg.encodeJPEG(88);
}

async function subir(nome: string, bin: Uint8Array, tipo: string) {
  const up = await db.storage.from("capas").upload(nome, bin, { contentType: tipo, upsert: true });
  if (up.error) throw new Error("storage: " + up.error.message);
  return db.storage.from("capas").getPublicUrl(nome).data.publicUrl;
}

// ---------- 4) Instagram ----------
async function ig(path: string, token: string, params: Record<string, string>, metodo = "GET") {
  const u = new URL("https://graph.instagram.com/v21.0" + path);
  const init: RequestInit = { method: metodo };
  if (metodo === "GET") { for (const [k, v] of Object.entries({ ...params, access_token: token })) u.searchParams.set(k, v); }
  else { init.body = new URLSearchParams({ ...params, access_token: token }); }
  const r = await fetch(u, init);
  const o = await r.json();
  if (o.error) throw new Error("ig " + path + ": " + o.error.message);
  return o;
}
async function postar(urls: string[], legenda: string) {
  const token = (await conf("ig_token")) ?? Deno.env.get("IG_ACCESS_TOKEN")!;
  const filhos: string[] = [];
  for (const url of urls) filhos.push((await ig(`/${IG_USER}/media`, token, { image_url: url, is_carousel_item: "true" }, "POST")).id);
  const cont = await ig(`/${IG_USER}/media`, token, { media_type: "CAROUSEL", children: filhos.join(","), caption: legenda }, "POST");
  for (let i = 0; i < 20; i++) {
    const st = await ig(`/${cont.id}`, token, { fields: "status_code" });
    if (st.status_code === "FINISHED") break;
    if (st.status_code === "ERROR") throw new Error("ig: container com erro");
    await new Promise((r) => setTimeout(r, 3000));
  }
  return (await ig(`/${IG_USER}/media_publish`, token, { creation_id: cont.id }, "POST")).id as string;
}

// ---------- fluxo ----------
Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ erro: "use POST" }, 405);
  const conv = await conf("yt_convite");
  if (!conv || req.headers.get("x-convite") !== conv) return json({ erro: "convite inválido" }, 401);
  const b = await req.json().catch(() => ({}));
  const publicar = b.modo === "publicar";
  try {
    if (publicar) {
      const desde = new Date(Date.now() - 20 * 3600 * 1000).toISOString();
      const { data: rec } = await db.from("publicacoes").select("id").eq("status", "carrossel").gte("criado_em", desde).limit(1);
      if (rec?.length) return json({ pulou: "já houve carrossel nas últimas 20h" });
    }
    // número do carrossel e produtos já usados
    const { data: chaves } = await db.from("config").select("chave").like("chave", "carrossel_%");
    const n = Math.max(0, ...(chaves ?? []).map((c: any) => parseInt(String(c.chave).split("_")[1]) || 0)) + 1;
    const num = String(n).padStart(3, "0");
    const { data: pubs } = await db.from("publicacoes").select("detalhe").eq("status", "carrossel");
    const usados = new Set<number>();
    for (const p of pubs ?? []) for (const m of String(p.detalhe ?? "").matchAll(/ids ([\d,]+)/g)) m[1].split(",").forEach((x) => usados.add(+x));

    const { data: cand } = await db.from("produtos").select("id,titulo,titulo_curto,preco,imagem_url,link_afiliado,vendidos")
      .eq("ativo", true).not("imagem_url", "is", null).not("link_afiliado", "is", null)
      .order("vendidos", { ascending: false, nullsFirst: false }).limit(60);
    const pool = (cand ?? []).filter((p: any) => !usados.has(p.id)).sort(() => Math.random() - 0.5);

    const slides: { p: any; bin: Uint8Array }[] = [];
    for (const p of pool) {
      if (slides.length === 5) break;
      try { slides.push({ p, bin: await slideProduto(p, slides.length + 1) }); } catch (_e) { /* tenta o próximo */ }
    }
    if (slides.length < 5) return json({ erro: "poucos produtos com foto utilizável", ok: slides.length }, 500);

    const idea = await ideia(slides.map((s) => s.p.titulo_curto || s.p.titulo));
    const capa = await gerarCapa(idea);

    const tag = `car${num}-${Date.now()}`;
    const urls: string[] = [await subir(`${tag}-0.png`, capa, "image/png")];
    for (let i = 0; i < slides.length; i++) urls.push(await subir(`${tag}-${i + 1}.jpg`, slides[i].bin, "image/jpeg"));
    urls.push(await subir(`${tag}-6.jpg`, await slideFinal(num), "image/jpeg"));

    const lista = slides.map((s, i) => `${i + 1}️⃣ ${s.p.titulo_curto || s.p.titulo} (${brl(s.p.preco)})`).join("\n");
    const legenda = `${idea.gancho}\n\n5 achadinhos da Shopee que valem cada centavo 👇\n${lista}\n\n` +
      `Comenta QUERO que eu te mando os links no direct 🧡\n\nCarrossel ${num}\n\n#achadinhos #shopee #achadinhosdashopee #garimpo #casa`;
    const resposta = `Segue os links que você solicitou do Carrossel ${num} 🧡\n` +
      slides.map((s, i) => `${i + 1}️⃣ ${s.p.titulo_curto || s.p.titulo} (${brl(s.p.preco)}) ${s.p.link_afiliado}`).join("\n") +
      `\nEntra no nosso grupo VIP de promoções, toda hora tem achado novo 👇 ${GRUPO}\n⚠️ Preço e disponibilidade podem mudar.`;

    if (!publicar) return json({ modo: "teste", numero: num, ideia: idea, legenda, urls });

    const midia = await postar(urls, legenda);
    await db.from("config").upsert({ chave: `carrossel_${num}`, valor: resposta, atualizado: new Date().toISOString() });
    await db.from("publicacoes").insert({ tipo: "feed", status: "carrossel", ig_media_id: midia, detalhe: `carrossel ${num}: ids ${slides.map((s) => s.p.id).join(",")}` });
    return json({ publicado: midia, numero: num, urls });
  } catch (e) {
    return json({ erro: String(e).slice(0, 400) }, 500);
  }
});
