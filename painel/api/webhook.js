// Campainha do Instagram: a Meta avisa aqui na hora em que chega um comentário ou mensagem.
// Só aceitamos avisos assinados com a chave secreta do app (META_APP_SECRET, guardada no Vercel)
// e repassamos para o robô (Supabase), que manda o link no Direct.
import crypto from "node:crypto";

const ROBO_URL = process.env.ROBO_URL || "https://qycdxxlzjlueyavmzkqy.supabase.co/functions/v1/robo";
const VERIFY_TOKEN = "achados-decoded-webhook"; // só serve para o "aperto de mão" inicial da Meta

async function corpoBruto(req) {
  const partes = [];
  for await (const c of req) partes.push(typeof c === "string" ? Buffer.from(c) : c);
  return Buffer.concat(partes);
}

export default async function handler(req, res) {
  // 1) Verificação inicial (a Meta chama com GET ao configurar o webhook)
  if (req.method === "GET") {
    const u = new URL(req.url, "http://x");
    if (u.searchParams.get("hub.mode") === "subscribe" && u.searchParams.get("hub.verify_token") === VERIFY_TOKEN) {
      return res.status(200).send(u.searchParams.get("hub.challenge"));
    }
    return res.status(403).send("forbidden");
  }
  if (req.method !== "POST") return res.status(405).send("method not allowed");

  // 2) Confere a assinatura da Meta
  const bruto = await corpoBruto(req);
  const assinatura = req.headers["x-hub-signature-256"] || "";
  const esperado = "sha256=" + crypto.createHmac("sha256", process.env.META_APP_SECRET || "").update(bruto).digest("hex");
  const ok = assinatura.length === esperado.length &&
    crypto.timingSafeEqual(Buffer.from(assinatura), Buffer.from(esperado));
  if (!ok) return res.status(401).send("assinatura inválida");

  // 3) Repassa para o robô e responde rápido para a Meta
  try {
    await fetch(`${ROBO_URL}?acao=webhook`, {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.SUPABASE_ANON_KEY}`, "Content-Type": "application/json" },
      body: bruto,
    });
  } catch (e) {
    console.error("robo indisponivel", e);
  }
  return res.status(200).send("ok");
}

export const config = { api: { bodyParser: false } };
