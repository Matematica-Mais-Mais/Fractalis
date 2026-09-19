import numpy as np
from PIL import Image
import sys
import colorsys
from sympy import diff, lambdify, solve, symbols

# ===============CONFIGURAÇÃO DO POLINÔMIO===============
x = symbols("x")
polinomio = x**3 - 1
derivada_polinomio = diff(polinomio, x)

# Para cada raiz do polinomio, converta em um valor númerico e depois transforme em um valor complexo
raizes_do_polinomio = [r.evalf() for r in solve(polinomio, x)]
raizes_do_polinomio = [complex(r) for r in raizes_do_polinomio]
numero_de_raizes = len(raizes_do_polinomio)
print(len(raizes_do_polinomio))

# Avaliação numérica rápida (lambdify converte a expressão simbólica em uma função Python normal que usa operações do NumPy que calcula tudo de uma vez)
func_polinomio = lambdify(x, polinomio, "numpy")
func_derivada = lambdify(x, derivada_polinomio, "numpy")

#Constantes do Programa
LARGURA_IMAGEM = 1000
ALTURA_IMAGEM = 1000
TOLERANCIA = 1
QTD_CHUTES = 50
FATOR_PASSO = 1

# [-2, 2] => Domínio (real e imaginário)

# ===============FUNÇÕES===============
def criar_malha_complexa(largura, altura):
    real = -2 + (np.arange(largura)[np.newaxis, :] / largura) * 4
    imaginaria = -2 + (np.arange(altura)[:, np.newaxis] / altura) * 4
    return real + 1j * imaginaria


def metodo_de_newton_vetorizado(pontos_iniciais):
    pontos_atuais = pontos_iniciais.copy() # Começa como uma cópia da malha (os "chutes iniciais" — um valor complexo por pixel). Essa variável vai sendo atualizada a cada iteração.
    pontos_ativos = np.ones(pontos_atuais.shape, dtype=bool) # Uma matriz de Trues, do mesmo formato, que funciona como um interruptor por pixel. Ela indica: "esse pixel ainda deve continuar sendo atualizado?" No início, todos estão ligados (True).

    # É necessário, uma vez que alguns podem cair exatamente onde a derivada é zero, e aí a fórmula de Newton quebra (divisão por zero). Precisamos "congelar" esses pontos sem travar o processo para os outros.

    for _ in range(QTD_CHUTES):
        # Calcula a derivada de todos os pontos de uma vez
        valor_derivada = func_derivada(pontos_atuais)

        # Desliga o interruptor desses pontos que possuem divisão por zero
        travados_por_derivada_zero = pontos_ativos & (valor_derivada == 0)
        pontos_ativos[travados_por_derivada_zero] = False

        # É um gerenciador de contexto que silencia  os avisos de "divisão por zero" temporariamente.
        with np.errstate(divide="ignore", invalid="ignore"):
            passo_newton = FATOR_PASSO  * func_polinomio(pontos_atuais) / valor_derivada # f(x) / f'(x)

        # pode_atualizar = pontos_ativos & (valor_derivada != 0)
        pontos_atuais = np.where(pontos_ativos, pontos_atuais - passo_newton, pontos_atuais)

    return pontos_atuais, pontos_ativos

def gerar_paleta_harmonica(num_cores, saturacao=0.7, brilho=0.9):
    if num_cores <= 0:
        return []
    
    paleta = []
    
    for i in range(num_cores):
        # Divide a roda de cores (0.0 a 1.0) em partes iguais
        hue = i / num_cores
        
        # Converte HSV para RGB
        r, g, b = colorsys.hsv_to_rgb(hue, saturacao, brilho)
        
        # Converte de 0.0-1.0 para a escala RGB 0-255
        cor_rgb = (int(r * 255), int(g * 255), int(b * 255))
        paleta.append(cor_rgb)
        
    return paleta

def colorir_por_raiz(valores_finais, pontos_ativos):
    raizes_array = np.array(raizes_do_polinomio)

    # Para cada pixel, ele calcula a diferença entre o valor final daquele pixel e todas as N raízes ao mesmo tempo.
    distancias_ate_raizes = np.abs(valores_finais[..., np.newaxis] - raizes_array)
    indice_raiz_mais_proxima = distancias_ate_raizes.argmin(axis=-1) 
    # indice_raiz_mais_proxima[500, 300] == 2, significa que o pixel na linha 500, coluna 300, convergiu para perto da raiz de índice 2.

    menor_distancia = distancias_ate_raizes.min(axis=-1)

    paleta = gerar_paleta_harmonica(numero_de_raizes)

    cores = np.zeros((*valores_finais.shape, 3), dtype=np.uint8)

    for i in range(0, numero_de_raizes):
        cores[indice_raiz_mais_proxima == i] = paleta[i]

    cores[~pontos_ativos] = (0, 0, 0)
    cores[menor_distancia >= TOLERANCIA] = (255, 255, 255)

    pixels_sem_convergencia = menor_distancia >= TOLERANCIA
    return cores, pixels_sem_convergencia


# ===============LÓGICA===============
# Só roda ao executar este arquivo diretamente (python raizes_complexas.py).
# Quando importado pelo app.py / Flask, esse bloco NÃO deve executar —
# senão o servidor trava minutos calculando um fractal 1000x1000 antes de subir.
if __name__ == "__main__":
    malha_complexa = criar_malha_complexa(LARGURA_IMAGEM, ALTURA_IMAGEM)
    valores_finais, pontos_ativos = metodo_de_newton_vetorizado(malha_complexa)
    cores_da_imagem, pixels_sem_convergencia = colorir_por_raiz(valores_finais, pontos_ativos)

    print(f"Pixels sem raiz reconhecida: {pixels_sem_convergencia.sum()}")

    imagem = Image.fromarray(cores_da_imagem)
    imagem.show()