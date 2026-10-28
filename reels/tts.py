"""Narração com a ElevenLabs, já com o tempo de cada palavra (para a legenda)."""
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

from render import Palavra

URL = "https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps?output_format=mp3_44100_128"


def narrar(texto: str, voz: str, chave: str, saida: Path, modelo: str = "eleven_multilingual_v2") -> list[Palavra]:
    corpo = json.dumps({
        "text": texto,
        "model_id": modelo,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True},
    }).encode()
    req = urllib.request.Request(URL.format(voz=voz), data=corpo, method="POST",
                                 headers={"xi-api-key": chave, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        j = json.load(r)

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
