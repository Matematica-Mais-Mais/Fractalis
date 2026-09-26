"""
Sistema de paletas de cores para o Fractalis.

Cada paleta tem uma lista base de cores (hex). gerar_cores() recebe o
nome da paleta e a quantidade de raízes necessária, e devolve exatamente
essa quantidade de cores:

- Se a quantidade pedida for <= quantidade de cores base: usa as
  primeiras N cores da paleta, na ordem em que foram definidas
  (ex.: só 2 raízes -> as 2 primeiras cores da paleta).
- Se for maior: mantém as cores base como as primeiras da lista e gera
  cores extras a partir delas (girando o matiz em HSL, mantendo a
  saturação/luminosidade médias da paleta), para completar a quantidade
  necessária sem repetir cor.

A geração automática de cores extras é uma opção separada, controlada
pelo parâmetro `gerar_automaticamente` de gerar_cores() (ligada por
padrão). Com ela desligada, pedir mais cores do que a paleta base tem
gera um erro em vez de inventar cores novas.
"""

import colorsys

PALETAS = {
    "homeblue": [
        "#003E8F",
        "#4F3B15",
        "#8F5E01",
        "#14243A",
        "#FFD482",
        "#ADD0FF",
    ],
    "coldblues": [
        "#68b2f8",
        "#506ee5",
        "#7037cd",
        "#651f71",
        "#1d0c20",
    ],
}


def _hex_para_rgb(cor_hex):
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_para_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(
        *[max(0, min(255, round(c))) for c in rgb]
    )


def _gerar_cores_extras(cores_base_rgb, quantidade_extra):
    hsl_base = []
    for r, g, b in cores_base_rgb:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        hsl_base.append((h, l, s))

    saturacao_media = sum(s for _, _, s in hsl_base) / len(hsl_base)
    luminosidade_media = sum(l for _, l, _ in hsl_base) / len(hsl_base)
    matiz_inicial = hsl_base[-1][0]

    cores_extras = []
    passo = 1.0 / (quantidade_extra + 1)
    for i in range(quantidade_extra):
        h = (matiz_inicial + passo * (i + 1)) % 1.0
        r, g, b = colorsys.hls_to_rgb(h, luminosidade_media, saturacao_media)
        cores_extras.append((r * 255, g * 255, b * 255))

    return cores_extras


def gerar_cores(nome_paleta, quantidade_raizes, gerar_automaticamente=True):
    """
    Retorna `quantidade_raizes` cores em hex a partir da paleta `nome_paleta`.

    `gerar_automaticamente` é a opção separada que liga/desliga a geração
    de cores extras quando a paleta base não tem cores suficientes. Se
    False e faltar cor, levanta ValueError em vez de gerar cores novas.
    """
    if nome_paleta not in PALETAS:
        raise ValueError(f"Paleta '{nome_paleta}' não encontrada.")
    if quantidade_raizes < 1:
        raise ValueError("A quantidade de raízes deve ser pelo menos 1.")

    base_hex = PALETAS[nome_paleta]

    if quantidade_raizes <= len(base_hex):
        return base_hex[:quantidade_raizes]

    if not gerar_automaticamente:
        raise ValueError(
            f"A paleta '{nome_paleta}' tem só {len(base_hex)} cores base e "
            "a geração automática de cores extras está desligada."
        )

    base_rgb = [_hex_para_rgb(c) for c in base_hex]
    extras_necessarias = quantidade_raizes - len(base_hex)
    cores_extras_rgb = _gerar_cores_extras(base_rgb, extras_necessarias)
    cores_extras_hex = [_rgb_para_hex(c) for c in cores_extras_rgb]

    return base_hex + cores_extras_hex


def gerador_de_paletas_PD(nome_paleta, quantidade_raizes, gerar_automaticamente=True):
    """Igual a gerar_cores(), mas devolve tuplas RGB (0-255) em vez de hex —
    formato que colorir_por_raiz() já espera (mesmo formato de
    gerar_paleta_harmonica)."""
    cores_hex = gerar_cores(nome_paleta, quantidade_raizes, gerar_automaticamente)
    return [_hex_para_rgb(c) for c in cores_hex]


if __name__ == "__main__":
    for n in (2, 6, 8, 12):
        print(n, "->", gerar_cores("homeblue", n))

    try:
        gerar_cores("homeblue", 8, gerar_automaticamente=False)
    except ValueError as erro:
        print("gerar_automaticamente=False com 8 raízes ->", erro)