"""Roda no GitHub Actions: pega o próximo produto, monta o Reel e manda publicar.

Variáveis (Secrets do repositório):
  ROBO_URL            https://<projeto>.supabase.co/functions/v1/robo
  SUPABASE_ANON_KEY   chave pública do projeto (a função exige)
  ELEVENLABS_API_KEY  chave da ElevenLabs
  ELEVENLABS_VOICE_ID voz escolhida
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

from render import Fontes, Roteiro, montar, montar_sobre_video, video_tem_letreiro
from tts import narrar

ROBO = os.environ["ROBO_URL"]
ANON = os.environ["SUPABASE_ANON_KEY"]
FONTES = Path(os.environ.get("FONTES_DIR", "fonts"))
PREVIA = os.environ.get("PREVIA", "").lower() == "true"  # só monta o vídeo, não posta
PRODUTO = os.environ.get("PRODUTO", "").strip().lstrip("#")  # nº do achado para postar agora (opcional)
MODO = os.environ.get("MODO", "").strip().lower()  # "foto" ou "video" (opcional, com PRODUTO)


def robo(acao: str, **params) -> dict:
    url = ROBO + "?" + urllib.parse.urlencode({"acao": acao, **params})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {ANON}"})
    with urllib.request.urlopen(req, timeout=140) as r:
        j = json.load(r)
    if j.get("erro") and acao != "checar":  # em "checar", erro=False/True é status, não falha
        raise RuntimeError(f"{acao}: {j['erro']}")
    return j


def baixar(url: str, destino: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        destino.write_bytes(r.read())


def enviar(url_assinada: str, arquivo: Path, tipo: str) -> None:
    req = urllib.request.Request(url_assinada, data=arquivo.read_bytes(), method="PUT",
                                 headers={"Content-Type": tipo, "x-upsert": "true"})
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()


# Chamada final falada (urgência sem prometer estoque que não sabemos)
CTAS = [
    "Gostou? Comenta EU QUERO que eu te mando o link no direct! É o achado número {n}.",
    "Quer o link? Comenta EU QUERO aqui embaixo que ele chega no seu direct. Corre que preço bom não dura!",
    "Comenta EU QUERO que eu te mando o link agora no direct. O preço pode mudar a qualquer hora!",
]


def foto_jpg(origem: Path, destino: Path) -> None:
    from PIL import Image
    Image.open(origem).convert("RGB").save(destino, "JPEG", quality=95)


def main() -> int:
    extra = {"previa": "1"} if PREVIA else {}
    if PRODUTO:
        extra["id"] = PRODUTO
        if MODO:
            extra["modo"] = MODO
    p = robo("proximo_reel", **extra)
    if p.get("pulado"):
        print("Nada a fazer:", p)
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        if p.get("video_base"):
            # vídeo pronto (anúncio da Shopee ou ilustrativo) + narração + caixinha no topo
            baixar(p["video_base"], d / "base.mp4")
            estoque = "pexels.com" in p["video_base"] or "pixabay.com" in p["video_base"]
            if estoque:  # vídeo de banco de imagens mostra a cena; o card mostra o produto de verdade
                baixar(p["imagem_url"], d / "foto_original")
                foto_jpg(d / "foto_original", d / "foto.jpg")
            letreiro = video_tem_letreiro(d / "base.mp4") if not estoque else False
            print("Vídeo já tem letreiro próprio:", letreiro)
            palavra = p.get("palavra") or "EU QUERO"
            cta = f"Comenta {palavra.upper()} que eu te mando o link!"
            texto = p["narracao"].rstrip() + " " + cta
            palavras = narrar(texto, os.environ["ELEVENLABS_VOICE_ID"], os.environ["ELEVENLABS_API_KEY"], d / "voz.mp3")
            montar_sobre_video(d / "base.mp4", p.get("frase_topo") or p["capa"], palavra, palavras, d / "voz.mp3",
                               Fontes(FONTES), d / "reel.mp4", d / "capa.jpg", n_cta=len(cta.split()),
                               aviso_ia="/ia/" in p["video_base"],
                               foto=(d / "foto.jpg") if estoque else None, preco=p["preco_txt"] if estoque else None,
                               legenda_on=not letreiro, som_original=False)
        else:
            baixar(p["imagem_url"], d / "foto_original")
            foto_jpg(d / "foto_original", d / "foto.jpg")

            cta = CTAS[int(p["numero"]) % len(CTAS)].format(n=p["numero"])
            texto = p["narracao"].rstrip() + " " + cta
            palavras = narrar(texto, os.environ["ELEVENLABS_VOICE_ID"], os.environ["ELEVENLABS_API_KEY"], d / "voz.mp3")
            roteiro = Roteiro(capa=p["capa"], beneficios=p["beneficios"], numero=p["numero"], preco=p["preco_txt"])
            montar(d / "foto.jpg", roteiro, palavras, d / "voz.mp3", Fontes(FONTES), d / "reel.mp4", d / "capa.jpg",
                   n_cta=len(cta.split()))

        enviar(p["upload_video"], d / "reel.mp4", "video/mp4")
        enviar(p["upload_capa"], d / "capa.jpg", "image/jpeg")

        # cópia para o TikTok (o workflow publica em Releases > videos)
        saida = Path(__file__).resolve().parent / "out"
        saida.mkdir(exist_ok=True)
        nome = f"{'previa-' if PREVIA else ''}achado-{p['numero']}-{int(time.time())}"
        (saida / f"{nome}.mp4").write_bytes((d / "reel.mp4").read_bytes())
        (saida / f"{nome}.txt").write_text(
            f"{p['capa']} 👀 Achado #{p['numero']} por {p['preco_txt']}! Link na bio 👉 procure o nº {p['numero']} "
            "#achadinhos #achadosdashopee #shopee #shopeebrasil #publi", encoding="utf-8")

    if PREVIA:
        print("PRÉVIA (não postado). Vídeo:", p["url_video"], "| Capa:", p["url_capa"])
        return 0

    # Instagram processa o vídeo em segundo plano; acompanhamos até ficar pronto
    c = robo("criar_reel", id=p["id"], video=p["caminho_video"], capa=p["caminho_capa"])
    for _ in range(40):
        st = robo("checar", reel=c["reel"], story=c["story"])
        if st["pronto"]:
            break
        if st["erro"]:
            raise RuntimeError(f"Instagram recusou o vídeo: {st}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram demorou demais para processar")

    r = robo("publicar_reel", id=p["id"], reel=c["reel"], story=c["story"], video=p["caminho_video"], modo=p.get("modo") or "foto")
    print("Publicado:", r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
