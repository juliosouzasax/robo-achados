"""Monta o Reel 9:16 de um produto.

Entrada: foto do produto, roteiro (capa, narração, benefícios) e a narração já
gerada com o tempo de cada palavra. Saída: reel.mp4 e capa.jpg.

Estrutura do vídeo (inspirada nos Reels de achadinhos que mais performam):
  - foto do produto com zoom lento sobre um fundo desfocado da própria foto
  - legenda palavra a palavra no centro, palavra-chave em amarelo
  - pílulas de benefício (✓) entrando uma a uma no meio do vídeo
  - selo da Shopee e marca fixa no topo, #publi
  - final com chamada "Link na bio · Achado #N"
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
LARANJA = (238, 77, 45)
AMARELO = (255, 205, 0)
BRANCO = (255, 255, 255)
PRETO = (25, 25, 25)


@dataclass
class Palavra:
    texto: str
    ini: float
    fim: float


@dataclass
class Roteiro:
    capa: str              # frase-gancho da capa, ex.: "Acabou a bagunça na pia"
    beneficios: list[str]  # 3 benefícios curtos
    numero: int            # número do achado na vitrine
    preco: str             # "R$ 26,98"


class Fontes:
    def __init__(self, pasta: Path):
        self.pasta = pasta

    def forte(self, tam: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.pasta / "Montserrat_800ExtraBold.ttf"), tam)

    def media(self, tam: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.pasta / "Montserrat_600SemiBold.ttf"), tam)


def _cobrir(img: Image.Image, w: int, h: int) -> Image.Image:
    """Redimensiona preenchendo w x h (corta o excesso)."""
    esc = max(w / img.width, h / img.height)
    nova = img.resize((math.ceil(img.width * esc), math.ceil(img.height * esc)), Image.LANCZOS)
    x, y = (nova.width - w) // 2, (nova.height - h) // 2
    return nova.crop((x, y, x + w, y + h))


def _suave(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _pilula(d: ImageDraw.ImageDraw, cx: int, y: int, texto: str, f: ImageFont.FreeTypeFont, fundo, cor):
    """Pílula arredondada com um ✓ desenhado (a fonte não tem o símbolo)."""
    larg = int(d.textlength(texto, font=f))
    icone, pad_x, alt = 46, 34, f.size + 34
    total = icone + larg + pad_x * 2
    x0 = cx - total // 2
    d.rounded_rectangle((x0, y, x0 + total, y + alt), radius=alt // 2, fill=fundo)
    cy = y + alt // 2
    xc = x0 + pad_x
    d.line([(xc, cy), (xc + 12, cy + 13), (xc + 32, cy - 14)], fill=(30, 150, 70), width=8, joint="curve")
    d.text((xc + icone, y + 14), texto, font=f, fill=cor)
    return alt


def _texto_contorno(d, xy, texto, f, cor):
    d.text(xy, texto, font=f, fill=cor, stroke_width=6, stroke_fill=(0, 0, 0))


def _grupos_legenda(palavras: list[Palavra], por_grupo: int = 2) -> list[tuple[float, float, list[str]]]:
    """Agrupa as palavras de 2 em 2, como nas legendas dinâmicas."""
    grupos = []
    for i in range(0, len(palavras), por_grupo):
        g = palavras[i : i + por_grupo]
        grupos.append((g[0].ini, g[-1].fim, [p.texto for p in g]))
    # cada grupo fica na tela até o próximo começar
    return [(ini, grupos[j + 1][0] if j + 1 < len(grupos) else fim + 0.4, txt) for j, (ini, fim, txt) in enumerate(grupos)]


def _palavra_chave(txt: list[str]) -> int:
    """Destaca a palavra mais longa do grupo (costuma ser a de sentido)."""
    return max(range(len(txt)), key=lambda i: len(txt[i].strip(".,!?")))


def montar(foto: Path, roteiro: Roteiro, palavras: list[Palavra], audio: Path, fontes: Fontes,
           saida_video: Path, saida_capa: Path) -> None:
    dur_fala = palavras[-1].fim if palavras else 8.0
    dur_cta = 2.6
    duracao = dur_fala + dur_cta
    n_frames = int(duracao * FPS)

    original = Image.open(foto).convert("RGB")
    fundo = _cobrir(original, W, H).filter(ImageFilter.GaussianBlur(40))
    fundo = Image.blend(fundo, Image.new("RGB", (W, H), (0, 0, 0)), 0.35)

    # foto do produto "grande" para o zoom
    base_foto = _cobrir(original, int(W * 0.92), int(W * 0.92))

    grupos = _grupos_legenda(palavras)
    ini_beneficios = dur_fala * 0.45

    f_marca = fontes.forte(40)
    f_pub = fontes.media(30)
    f_leg = fontes.forte(84)
    f_pil = fontes.forte(46)
    f_cta = fontes.forte(58)
    f_sub = fontes.forte(40)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(audio),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
         "-af", "apad", "-t", f"{n_frames / FPS:.3f}",  # silêncio no fim cobre a chamada final
         "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart",
         str(saida_video)],
        stdin=subprocess.PIPE,
    )

    for n in range(n_frames):
        t = n / FPS
        quadro = fundo.copy()

        # zoom lento contínuo (Ken Burns) na foto do produto
        z = 1.0 + 0.18 * (t / duracao)
        lado = int(base_foto.width / z)
        ox = max(0, min(base_foto.width - lado, (base_foto.width - lado) // 2 + int(30 * math.sin(t * 0.6))))
        oy = (base_foto.height - lado) // 2
        recorte = base_foto.crop((ox, oy, ox + lado, oy + lado)).resize((base_foto.width, base_foto.height), Image.BILINEAR)
        mascara = Image.new("L", recorte.size, 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, *recorte.size), radius=48, fill=255)
        px = (W - recorte.width) // 2
        py = 300
        quadro.paste(recorte, (px, py), mascara)

        d = ImageDraw.Draw(quadro)

        # marca no topo
        d.rounded_rectangle((40, 60, 104, 124), radius=16, fill=LARANJA)
        d.text((56, 66), "A", font=fontes.forte(44), fill=BRANCO)
        d.text((122, 70), "achadosdecoded", font=f_marca, fill=BRANCO)
        larg_pub = d.textlength("#publi", font=f_pub)
        d.rounded_rectangle((W - 60 - larg_pub - 30, 70, W - 60, 118), radius=24, fill=(0, 0, 0, 160))
        d.text((W - 60 - larg_pub - 15, 76), "#publi", font=f_pub, fill=BRANCO)

        # preço
        tag = roteiro.preco
        lt = d.textlength(tag, font=fontes.forte(56))
        d.rounded_rectangle((px + 30, py + recorte.height - 110, px + 30 + lt + 50, py + recorte.height - 30), radius=20, fill=LARANJA)
        d.text((px + 55, py + recorte.height - 104), tag, font=fontes.forte(56), fill=BRANCO)

        # pílulas de benefício
        if t >= ini_beneficios and t < dur_fala:
            y = 1360
            for i, b in enumerate(roteiro.beneficios[:3]):
                aparece = ini_beneficios + i * 0.5
                if t >= aparece:
                    destaque = i == 0
                    y += _pilula(d, W // 2, y, b, f_pil,
                                 AMARELO if destaque else BRANCO, PRETO) + 16

        # legenda palavra a palavra
        if t < dur_fala:
            atual = next((g for g in grupos if g[0] <= t < g[1]), None)
            if atual:
                txt = [w.upper() for w in atual[2]]
                k = _palavra_chave(atual[2])
                total = sum(d.textlength(w + " ", font=f_leg) for w in txt)
                x = (W - total) // 2
                yl = 1420 if t < ini_beneficios else 1720
                for i, w in enumerate(txt):
                    _texto_contorno(d, (x, yl), w, f_leg, AMARELO if i == k else BRANCO)
                    x += d.textlength(w + " ", font=f_leg)

        # chamada final
        if t >= dur_fala:
            p = _suave((t - dur_fala) / 0.35)
            yc = int(1560 + (1 - p) * 120)
            msg = "LINK NA BIO"
            lc = d.textlength(msg, font=f_cta)
            d.rounded_rectangle(((W - lc) // 2 - 60, yc, (W + lc) // 2 + 60, yc + 120), radius=60, fill=LARANJA)
            d.text(((W - lc) // 2, yc + 28), msg, font=f_cta, fill=BRANCO)
            sub = f"Procure o Achado #{roteiro.numero} na vitrine"
            ls = d.textlength(sub, font=f_sub)
            _texto_contorno(d, ((W - ls) // 2, yc + 150), sub, f_sub, BRANCO)

        ff.stdin.write(quadro.tobytes())

    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg falhou")

    _capa(original, roteiro, fontes, saida_capa)


def _capa(original: Image.Image, roteiro: Roteiro, fontes: Fontes, saida: Path) -> None:
    """Capa no estilo da referência: frase-gancho num cartão branco + foto."""
    capa = _cobrir(original, W, H).filter(ImageFilter.GaussianBlur(30))
    capa = Image.blend(capa, Image.new("RGB", (W, H), (0, 0, 0)), 0.25)
    d = ImageDraw.Draw(capa)
    f = fontes.forte(96)

    # quebra a frase em até 3 linhas
    palavras, linhas, atual = roteiro.capa.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if d.textlength(teste, font=f) <= W - 220:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    linhas.append(atual)
    linhas = linhas[:3]

    alt_txt = len(linhas) * 112
    y0 = 300
    d.rounded_rectangle((70, y0, W - 70, y0 + alt_txt + 80), radius=40, fill=BRANCO)
    y = y0 + 40
    for l in linhas:
        d.text(((W - d.textlength(l, font=f)) // 2, y), l, font=f, fill=PRETO)
        y += 112

    foto = _cobrir(original, 820, 820)
    m = Image.new("L", foto.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, *foto.size), radius=40, fill=255)
    borda = Image.new("RGB", (foto.width + 24, foto.height + 24), AMARELO)
    mb = Image.new("L", borda.size, 0)
    ImageDraw.Draw(mb).rounded_rectangle((0, 0, *borda.size), radius=48, fill=255)
    yf = y0 + alt_txt + 160
    capa.paste(borda, ((W - borda.width) // 2, yf), mb)
    capa.paste(foto, ((W - foto.width) // 2, yf + 12), m)
    capa.save(saida, "JPEG", quality=90)
