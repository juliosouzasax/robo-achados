"""Narração com a ElevenLabs, já com o tempo de cada palavra (para a legenda)."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from render import Palavra

URL = "https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps?output_format=mp3_44100_128"


# Eleven v4 é o modelo mais natural/emotivo; se a API recusar, cai no v2
MODELOS = [
    ("eleven_v4", {"stability": 0.5, "similarity_boost": 0.8}),
    ("eleven_multilingual_v2", {"stability": 0.35, "similarity_boost": 0.8, "style": 0.45, "use_speaker_boost": True}),
]


def _pedir(texto: str, voz: str, chave: str, modelo: str, ajustes: dict) -> dict:
    corpo = {"text": texto, "model_id": modelo, "voice_settings": ajustes}
    if modelo.startswith("eleven_v4"):
        corpo["language_code"] = "pt"
    corpo = json.dumps(corpo).encode()
    req = urllib.request.Request(URL.format(voz=voz), data=corpo, method="POST",
                                 headers={"xi-api-key": chave, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def narrar(texto: str, voz: str, chave: str, saida: Path) -> list[Palavra]:
    erro = None
    for modelo, ajustes in MODELOS:
        try:
            j = _pedir(texto, voz, chave, modelo, ajustes)
            if j.get("alignment"):
                print("Voz gerada com", modelo)
                break
        except urllib.error.HTTPError as e:
            erro = f"{modelo}: {e.code} {e.read()[:300]!r}"
            print("Modelo recusado ->", erro)
    else:
        raise RuntimeError(f"ElevenLabs falhou: {erro}")

    saida.write_bytes(base64.b64decode(j["audio_base64"]))
    al = j["alignment"]
    return _palavras(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"])


def _palavras(chars: list[str], ini: list[float], fim: list[float]) -> list[Palavra]:
    out, atual, t0, t1 = [], "", None, 0.0
    for c, a, b in zip(chars, ini, fim):
        if c.isspace():
            if atual:
                out.append(Palavra(atual, t0, t1))
            atual, t0 = "", None
            continue
        if t0 is None:
            t0 = a
        atual += c
        t1 = b
    if atual:
        out.append(Palavra(atual, t0, t1))
    return out
