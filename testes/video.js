// Teste: a página da Shopee abre num navegador do GitHub e mostra o vídeo do anúncio?
const { chromium } = require("playwright");
const fs = require("fs");
(async () => {
  const urls = fs.readFileSync("testes/video.txt", "utf8").split("\n").map((s) => s.trim()).filter(Boolean);
  const b = await chromium.launch();
  const ctx = await b.newContext({ locale: "pt-BR", userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", viewport: { width: 1366, height: 900 } });
  for (const u of urls) {
    const p = await ctx.newPage();
    const mp4 = new Set();
    p.on("request", (r) => { if (/vod\.susercontent\.com.*\.mp4/.test(r.url())) mp4.add(r.url().split("?")[0]); });
    try {
      await p.goto(u, { waitUntil: "domcontentloaded", timeout: 45000 });
      await p.waitForTimeout(9000);
      const r = await p.evaluate(() => { const v = document.querySelector("[class*=center] video") || document.querySelector("video"); return { titulo: document.title, url: location.href.split("?")[0], video: v ? (v.currentSrc || v.src || "") : null }; });
      console.log("RESULTADO", JSON.stringify({ ...r, mp4: [...mp4] }));
    } catch (e) { console.log("ERRO", u, String(e).slice(0, 200)); }
    await p.close();
  }
  await b.close();
})();
