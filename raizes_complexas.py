import numpy as np
from PIL import Image
import sys
import colorsys
from sympy import diff, lambdify, solve, symbols, solveset, nsolve, ConditionSet, Interval, pi

# ===============ÁREA DE DEBUG===============
# Tudo aqui dentro só roda se você executar o python raizes_complexas.py
# Quando o app.py importa este módulo (uso normal, via interface web), esta
# função nunca é chamada — o Flask define seu próprio polinômio a partir do
# que o usuário digitou e chama as funções acima diretamente.
 
#Constantes do Programa
# Esses valores só valem quando o script roda sozinho (área de debug, lá embaixo).
# Quando importado pelo app.py, o Flask sobrescreve todos eles a cada requisição.
LARGURA_IMAGEM = 1000
ALTURA_IMAGEM = 1000
TOLERANCIA = 1
QTD_CHUTES = 50
FATOR_PASSO = 1

# TOLERANCIA (acima) decide se um pixel "pertence" a alguma raiz no final —
# é ela que pinta de branco quem não convergiu. Para medir a VELOCIDADE de
# convergência (o brilho, explicado mais abaixo) usamos uma tolerância bem
# mais apertada. Se usássemos a mesma TOLERANCIA=1 pra isso, quase todo pixel
# "convergeria" já na primeira iteração e o brilho nunca variaria.
TOLERANCIA_BRILHO = 1e-6
 
# Controlam o "brilho por velocidade de convergência": pixels que convergem
# rápido para uma raiz ficam com a cor "pura" da paleta; pixels que demoram
# mais (tipicamente perto das fronteiras entre bacias de atração) ficam
# progressivamente mais claros, até um teto. É a mesma ideia da versão
# escalar antiga do projeto (aquela com if/elif por pixel), só que
# vetorizada e generalizada para qualquer número de raízes.
FATOR_BRILHO = 20
BRILHO_MAXIMO = 100
EH_SOMBRA = False

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

    # Guarda em que iteração cada pixel deu um passo de Newton pequeno o suficiente pra já considerar "convergido" (usa TOLERANCIA_BRILHO). Começa em QTD_CHUTES — o "pior caso": quem nunca convergir mantém esse valor, mas como esses pixels também caem no filtro de TOLERANCIA em colorir_por_raiz (viram branco ou preto), isso não afeta o resultado. Ainda_nao_convergiu garante que só gravamos a PRIMEIRA vez que isso acontece — sem precisar parar de atualizar o pixel por causa disso (continuar rodando Newton num ponto que já convergiu não faz mal: o passo já está minúsculo, então o valor não muda quase nada). 
    iteracao_de_convergencia = np.full(pontos_atuais.shape, QTD_CHUTES, dtype=np.int32) 
    ainda_nao_convergiu = np.ones(pontos_atuais.shape, dtype=bool)

    for iteracao in range(QTD_CHUTES):
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

        # Convergência medida pelo tamanho do passo de Newton — quando ele fica minúsculo, o ponto já estabilizou perto de um zero da função.
        convergiu_agora = ainda_nao_convergiu & (np.abs(passo_newton) < TOLERANCIA_BRILHO)
        iteracao_de_convergencia[convergiu_agora] = iteracao
        ainda_nao_convergiu[convergiu_agora] = False

    return pontos_atuais, pontos_ativos, iteracao_de_convergencia

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

def colorir_por_raiz(valores_finais, pontos_ativos, numero_de_raizes, iteracoes_de_convergencia=None):
    raizes_array = np.array(raizes_do_polinomio)

    # Para cada pixel, ele calcula a diferença entre o valor final daquele pixel e todas as N raízes ao mesmo tempo.
    distancias_ate_raizes = np.abs(valores_finais[..., np.newaxis] - raizes_array)
    indice_raiz_mais_proxima = distancias_ate_raizes.argmin(axis=-1) 
    # indice_raiz_mais_proxima[500, 300] == 2, significa que o pixel na linha 500, coluna 300, convergiu para perto da raiz de índice 2.

    menor_distancia = distancias_ate_raizes.min(axis=-1)

    paleta = gerar_paleta_harmonica(numero_de_raizes)
    paleta_array = np.array(paleta, dtype=np.int16)  # shape (numero_de_raizes, 3)

    # Cor "pura" de cada pixel, olhando só pra raiz mais próxima.
    cores_base = paleta_array[indice_raiz_mais_proxima]  # shape (altura, largura, 3)

    if iteracoes_de_convergencia is not None:
        # Brilho cresce com o número de iterações até a convergência, com um
        # teto (BRILHO_MAXIMO). Pixels perto do "centro" de uma bacia de
        # atração convergem rápido e ficam com a cor pura; pixels perto das
        # fronteiras entre bacias demoram mais e ficam progressivamente mais
        # claros — é isso que cria aqueles anéis/faixas característicos do
        # fractal de Newton.
        brilho = np.minimum(iteracoes_de_convergencia * FATOR_BRILHO, BRILHO_MAXIMO)
        cores = cores_base + brilho[..., np.newaxis]
        cores = np.clip(cores, 0, 255).astype(np.uint8)
    else:
        # Compatibilidade: se alguém ainda chamar colorir_por_raiz sem passar
        # o terceiro retorno de metodo_de_newton_vetorizado, cai de volta pra
        # cor pura, sem brilho.
        cores = cores_base.astype(np.uint8)
 
    cores[~pontos_ativos] = (0, 0, 0)
    cores[menor_distancia >= TOLERANCIA] = (255, 255, 255)
 
    pixels_sem_convergencia = menor_distancia >= TOLERANCIA
    return cores, pixels_sem_convergencia


def encontrar_raizes(polinomio, x, intervalo=None, n_chutes=100, precisao=6):
    """Aceita polinômio puro, trig pura ou composição (ex: x**2 - cos(x))."""
    if intervalo is None:
        intervalo = Interval(-4 * pi, 4 * pi)

    if polinomio.is_polynomial(x):
        # Polinômio puro -> solve() é exato e mais rápido
        raizes_do_polinomio = [r.evalf() for r in solve(polinomio, x)]
    else:
        # Trigonométrica / transcendental / composição -> tenta solveset
        # simbólico dentro do intervalo primeiro
        resultado = solveset(polinomio, x, domain=intervalo)

        if not isinstance(resultado, ConditionSet):
            # solveset conseguiu -> usa direto (mais preciso)
            raizes_do_polinomio = [r.evalf() for r in resultado]
        else:
            # solveset falhou (equação mista/transcendental complexa) -> nsolve
            a, b = float(intervalo.start), float(intervalo.end)
            chutes_iniciais = np.linspace(a, b, n_chutes)

            raizes_encontradas = set()
            for chute in chutes_iniciais:
                try:
                    raiz = nsolve(polinomio, x, chute)
                    raizes_encontradas.add(round(float(raiz), precisao))
                except Exception:
                    pass
            raizes_do_polinomio = list(raizes_encontradas)

    return [complex(r) for r in raizes_do_polinomio]


def debug():
    global func_polinomio, func_derivada, raizes_do_polinomio
 
    # Troque o polinômio abaixo à vontade para testar rapidamente, sem precisar
    # subir o Flask nem passar pela interface web. Agora também aceita
    # trigonométricas (ex: cos(x)) e composições (ex: x**2 - sin(x)).
    x = symbols("x")
    polinomio_debug = x**3 - 1
    derivada_debug = diff(polinomio_debug, x)
 
    raizes = encontrar_raizes(polinomio_debug, x)
    print("Raízes encontradas:", raizes)
 
    func_polinomio = lambdify(x, polinomio_debug, "numpy")
    func_derivada = lambdify(x, derivada_debug, "numpy")
    raizes_do_polinomio = raizes
    numero_de_raizes = len(raizes)
 
    malha_complexa = criar_malha_complexa(LARGURA_IMAGEM, ALTURA_IMAGEM)
    valores_finais, pontos_ativos, iteracoes_de_convergencia = metodo_de_newton_vetorizado(malha_complexa)
    cores_da_imagem, pixels_sem_convergencia = colorir_por_raiz(
        valores_finais, pontos_ativos, numero_de_raizes, iteracoes_de_convergencia
    )
 
    print(f"Pixels sem raiz reconhecida: {pixels_sem_convergencia.sum()}")
 
    imagem = Image.fromarray(cores_da_imagem)
    imagem.show()


if __name__ == "__main__":
    debug() 