import base64
import importlib.util
import io
import os
import sys
import time
import threading
import webbrowser
from flask import Flask, jsonify, render_template, request
from PIL import Image
from sympy import diff, lambdify, solve, symbols, sympify

app = Flask(__name__)

# Desativa a abertura automática de janelas do script original (imagem.show())
Image.Image.show = lambda self: None

# Função para localizar arquivos tanto no Python normal quanto dentro do .exe compilado
def caminho_recurso(caminho_relativo):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, caminho_relativo)
    return os.path.join(os.path.abspath("."), caminho_relativo)

# Importa o script original mantendo ele intacto
NOME_SCRIPT = caminho_recurso("raizes_complexas.py")
spec = importlib.util.spec_from_file_location("script_orig", NOME_SCRIPT)
script_orig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script_orig)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/gerar", methods=["POST"])
def gerar():
    try:
        tempo_inicio = time.time()
        dados = request.get_json() or {}

        expr_str = dados.get("polinomio", "x**10 - x**2 + 1").replace("^", "**")
        x = symbols("x")
        polinomio_expr = sympify(expr_str)
        derivada_expr = diff(polinomio_expr, x)

        raizes = script_orig.encontrar_raizes(polinomio_expr, x)

        script_orig.func_polinomio = lambdify(x, polinomio_expr, "numpy")
        script_orig.func_derivada = lambdify(x, derivada_expr, "numpy")
        script_orig.raizes_do_polinomio = raizes

        script_orig.LARGURA_IMAGEM = int(dados.get("largura", 600))
        script_orig.ALTURA_IMAGEM = int(dados.get("altura", 600))
        script_orig.QTD_CHUTES = int(dados.get("qtd_chutes", 50))
        script_orig.FATOR_PASSO = float(dados.get("fator_passo", 1.0))
        script_orig.TOLERANCIA = float(dados.get("tolerancia", 0.00001))

        malha = script_orig.criar_malha_complexa(
            script_orig.LARGURA_IMAGEM, script_orig.ALTURA_IMAGEM
        )
        valores_finais, pontos_ativos = script_orig.metodo_de_newton_vetorizado(malha)
        
        cores, pixels_sem_conv = script_orig.colorir_por_raiz(
            valores_finais, pontos_ativos, len(raizes)
        )

        img = Image.fromarray(cores)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        tempo_total = round(time.time() - tempo_inicio, 2)
        lista_raizes = [
            f"z{i+1}: {r.real:.3f} {'+' if r.imag >= 0 else ''}{r.imag:.3f}i"
            for i, r in enumerate(raizes)
        ]

        return jsonify({
            "sucesso": True,
            "imagem": f"data:image/png;base64,{img_b64}",
            "pixels_sem_convergencia": int(pixels_sem_conv.sum()),
            "qtd_raizes": len(raizes),
            "tempo": f"{tempo_total}s",
            "raizes": lista_raizes,
        })

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400


def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Programa a abertura do navegador 1.2 segundos após subir o servidor
    threading.Timer(1.2, abrir_navegador).start()
    app.run(port=5000, debug=False)