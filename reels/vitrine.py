"""Gera a vitrine (link na bio) como página estática em ../site/index.html.

Roda no GitHub Actions; a página não carrega nenhuma chave, só os links de afiliado.
"""
from __future__ import annotations

import html
import json
import os
import urllib.request
from pathlib import Path

ROBO = os.environ["ROBO_URL"]
ANON = os.environ["SUPABASE_ANON_KEY"]
SAIDA = Path(__file__).resolve().parent.parent / "site"


def brl(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def produtos() -> list[dict]:
    req = urllib.request.Request(ROBO + "?acao=vitrine", headers={"Authorization": f"Bearer {ANON}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["produtos"]


def cartao(p: dict) -> str:
    nome = html.escape(p.get("titulo_curto") or p["titulo"])
    busca = html.escape(f'{p["id"]} {p.get("titulo_curto") or ""} {p["titulo"]} {p.get("categoria") or ""}'.lower())
    return f'''<a class="item" href="{html.escape(p["link_afiliado"])}" target="_blank" rel="noopener sponsored" data-busca="{busca}">
  <span class="num">#{p["id"]}</span>
  <img src="{html.escape(p["imagem_url"])}" alt="" loading="lazy" referrerpolicy="no-referrer">
  <span class="info"><span class="nome">{nome}</span><span class="preco">{brl(float(p["preco"]))}</span></span>
  <span class="ir">Ver</span>
</a>'''


PAGINA = """<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Achados Decoded</title>
<meta name="description" content="Os achadinhos da Shopee do @achadosdecoded. Procure pelo número do vídeo.">
<style>
:root{--laranja:#ee4d2d;--fundo:#fff7f4;--texto:#1f1f1f;--cinza:#6b6b6b;--cartao:#fff;--borda:#f1dcd5}
@media (prefers-color-scheme:dark){:root{--fundo:#141110;--texto:#f4eeec;--cinza:#a9a09d;--cartao:#1f1a18;--borda:#332926}}
*{box-sizing:border-box}body{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--laranja);color:#fff;padding:28px 16px 22px;text-align:center}
header h1{margin:0;font-size:24px;letter-spacing:.5px}header p{margin:6px 0 0;opacity:.92;font-size:14px}
.busca{position:sticky;top:0;background:var(--fundo);padding:12px 16px;z-index:2;border-bottom:1px solid var(--borda)}
.busca input{width:100%;font-size:17px;padding:12px 14px;border-radius:12px;border:2px solid var(--borda);background:var(--cartao);color:var(--texto)}
.busca input:focus{outline:none;border-color:var(--laranja)}
main{max-width:560px;margin:0 auto;padding:12px 16px 32px;display:grid;gap:10px}
.item{display:grid;grid-template-columns:auto 72px 1fr auto;align-items:center;gap:12px;padding:10px 12px;background:var(--cartao);border:1px solid var(--borda);border-radius:14px;color:inherit;text-decoration:none}
.item:active{transform:scale(.99)}
.num{font-weight:800;color:var(--laranja);min-width:34px;font-size:15px}
.item img{width:72px;height:72px;object-fit:cover;border-radius:10px;background:#eee}
.info{display:flex;flex-direction:column;min-width:0}.nome{font-weight:600;font-size:15px}
.preco{color:var(--cinza);font-size:14px;margin-top:2px}
.ir{background:var(--laranja);color:#fff;font-weight:700;font-size:14px;padding:9px 14px;border-radius:999px}
.vazio{text-align:center;color:var(--cinza);padding:30px 0;display:none}
footer{text-align:center;color:var(--cinza);font-size:12px;padding:0 16px 28px;max-width:560px;margin:0 auto}
</style></head><body>
<header><h1>ACHADOS DECODED</h1><p>Viu no vídeo? Procure pelo número do achado 👇</p></header>
<div class="busca"><input id="q" type="search" inputmode="search" placeholder="Digite o nº ou o nome (ex: 12)" autocomplete="off"></div>
<main id="lista">
__ITENS__
<p class="vazio" id="vazio">Nenhum achado com esse número ou nome.</p>
</main>
<footer>Links de afiliado da Shopee (#publi): você paga o mesmo e o perfil ganha uma pequena comissão. Preço e estoque podem mudar a qualquer momento.</footer>
<script>
const q=document.getElementById('q'),itens=[...document.querySelectorAll('.item')],vazio=document.getElementById('vazio');
function filtrar(){const t=q.value.trim().toLowerCase().replace('#','');let n=0;
for(const i of itens){const ok=!t||(/^\\d+$/.test(t)?i.querySelector('.num').textContent==='#'+t:i.dataset.busca.includes(t));i.style.display=ok?'':'none';if(ok)n++}
vazio.style.display=n?'none':'block'}
q.addEventListener('input',filtrar);
const h=location.hash.replace('#','');if(h){q.value=h;filtrar()}
</script>
</body></html>
"""


def main() -> None:
    lista = produtos()
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "index.html").write_text(PAGINA.replace("__ITENS__", "\n".join(cartao(p) for p in lista)), encoding="utf-8")
    (SAIDA / ".nojekyll").write_text("")
    print(f"Vitrine com {len(lista)} achados")


if __name__ == "__main__":
    main()
