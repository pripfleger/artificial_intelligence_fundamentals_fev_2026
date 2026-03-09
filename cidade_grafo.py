# ARQUIVO PARA CRIAÇÃO DA CIDADE E MAPA
# Empresa Sabor Express é um ponto fixo
# Execute apenas UMA VEZ
# Para alterar é só editar as constantes e rodar novamente.

import numpy as np # faz cálculos numéricos e geração de coordenadas aleatórias
import random # gera aleatoriedade na criação do grafo
import pickle # salvar/carregar o grafo em arquivo
import matplotlib.pyplot as plt # gera o desenho do mapa
import networkx as nx # cria e manipula o grafo

SEED_CIDADE      = 42 # gera uma sequencia específica de números, representando sempre a mesma cidade, se alterar, altera a cidade.
GRADE            = 30 # tamanho da cidade como uma malha de 30x30
ESPACAMENTO_BASE = 10 # distância base entre cruzamentos
VARIACAO         = 0.25 # variação de ±25% no espaçamento
SABOR_EXPRESS    = (120, 85) # coordenada fixa do ponto de partida para as entregas
MAPA_CIDADE   = 'mapacidade.pkl'

# FUNÇÃO PARA CRIAR A CIDADE
def criar_cidade():
    random.seed(SEED_CIDADE) # fixa o random, usado para gerar as posições (x, y) dos nós, garantindo que o mapa não mude
    np.random.seed(SEED_CIDADE) # fixa o numpy, usado pra cálculos, ambos garantem que os nós do mapa sejam sempre os mesmos

    G = nx.Graph() # gera um grafo em branco

    def gerar_posicoes(n): # Gera n posições a partir de 0, com espaçamentos variáveis, para parecer um pouco mais real
        posicoes = [0]
        for _ in range(n - 1):
            distancia = ESPACAMENTO_BASE * random.uniform(1 - VARIACAO, 1 + VARIACAO)
            posicoes.append(round(posicoes[-1] + distancia, 2))
        return posicoes

    xs = gerar_posicoes(GRADE)   # gera coordenadas x de cada coluna
    ys = gerar_posicoes(GRADE)   # gera coordenadas y de cada linha

    # Criação dos nós da grade
    grade_ids = {} # conjunto de dicionários que identifica o nó e a linha/coluna de cada nó
    id_no = 0 # identificador do nó começa em 0

    for linha in range(GRADE):
        grade_ids[linha] = {}
        for col in range(GRADE):
            x = xs[col]
            y = ys[linha]
            G.add_node(id_no, pos=(x, y), tipo='cruzamento', label=f"N{id_no}", grade=(linha, col)) # adiciona os nós no mapa e identifica como cruzamento pois são as intersecções das linhas/colunas
            grade_ids[linha][col] = id_no
            id_no += 1

    # Cria as arestas horizontais e verticais a partir de nós vizinhos
    for linha in range(GRADE):
        for col in range(GRADE):
            no = grade_ids[linha][col]
            x1, y1 = G.nodes[no]['pos']

            # vizinho à direita
            if col + 1 < GRADE: # fazer com que seja menor que a grade evita que passe do limite desejado da malha
                viz = grade_ids[linha][col + 1]
                x2, y2 = G.nodes[viz]['pos']
                peso = round(np.sqrt((x2-x1)**2 + (y2-y1)**2), 2)
                G.add_edge(no, viz, weight=peso) # o peso é a distância euclidiana entre os dois nós

            # vizinho acima
            if linha + 1 < GRADE:
                viz = grade_ids[linha + 1][col]
                x2, y2 = G.nodes[viz]['pos']
                peso = round(np.sqrt((x2-x1)**2 + (y2-y1)**2), 2)
                G.add_edge(no, viz, weight=peso)

    # Marca o nó mais próximo da posição definida do SABOR_EXPRESS, como ponto fixo de partida
    sx, sy = SABOR_EXPRESS
    saborexpress_no = min(G.nodes, key=lambda n: np.sqrt((G.nodes[n]['pos'][0] - sx)**2 + (G.nodes[n]['pos'][1] - sy)**2)) # calcula a menor distância euclidiana (baseado no teorema de pitágoras)
    G.nodes[saborexpress_no]['tipo']  = 'sabor_express' # define o tipo do nó
    G.nodes[saborexpress_no]['label'] = 'SE' # define o rótulo para identificar o nó

    print(f"  Sabor Express → nó {saborexpress_no}  pos={G.nodes[saborexpress_no]['pos']}") # mostra na saída as coordenadas ajustadas da Empresa.

    return G, grade_ids, saborexpress_no

# SALVA O GRAFO DA CIDADE EM UM ARQUIVO
def salvar_cidade(G, grade_ids, saborexpress_no):
    with open(MAPA_CIDADE, 'wb') as mapa: # vai abrir o arquivo e escrever nele em formato binário, se o arquivo já existir, irá sobrescrever
        pickle.dump({'grafo': G, 'grade_ids': grade_ids, 'saborexpress_no':  saborexpress_no}, mapa)
    print(f"  Cidade salva em '{MAPA_CIDADE}'") # mostra na saída qual o nome do arquivo que tem o mapa salvo

# VISUAlIZAÇÃO DO MAPA
def visualizar_cidade(G, saborexpress_no):
    fig, ax = plt.subplots(figsize=(16, 16)) # cria a janela com 16x16 polegadas e a área do mapa delimitada pelos eixos
    ax.set_facecolor('#f7f4ef') # define a cor de fundo do mapa
    fig.patch.set_facecolor('#f7f4ef') # define a cor de fundo da janela

    # ARESTAS (RUAS)
    for u, v in G.edges(): # busca as coordenadas de dois nós, u e v
        xu, yu = G.nodes[u]['pos']
        xv, yv = G.nodes[v]['pos']
        ax.plot([xu, xv], [yu, yv], color='#aaaaaa', linewidth=0.8, zorder=1) # plota a linha (aresta) entre os nós representando a rua

    # CRUZAMENTOS (NÓS)
    cruzamentos = [numero for numero, dict in G.nodes(data=True) if dict['tipo'] == 'cruzamento'] # pega somente os nós definidos como tipo cruzamento
    xc = [G.nodes[numero]['pos'][0] for numero in cruzamentos]
    yc = [G.nodes[numero]['pos'][1] for numero in cruzamentos]
    ax.scatter(xc, yc, color='#2c3e50', s=10, zorder=2) # "distribui" os nós no mapa, para que fiquem por cima (zorder = 2) das linhas cruzadas (zorder = 1)

    # EMPRESA (Sabor Express)
    xse, yse = G.nodes[saborexpress_no]['pos'] # pega as coordenadas da empresa
    ax.scatter(xse, yse, color='#e74c3c', s=150, marker='*', zorder=4) # plota o nó que representa a empresa em formato de estrela
    ax.annotate('Sabor Express', (xse, yse), textcoords="offset points", xytext=(8, 8), fontsize=10, fontweight='bold', color='#e74c3c', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#e74c3c', alpha=0.9)) # plota o nome da empresa próximo do nó
    ax.set_title("Mapa da Cidade — Malha 30×30", fontsize=14, fontweight='bold', pad=15) # plota o título do mapa
    ax.set_xlabel("x", fontsize=11) # plota o rótulo do eixo x como x
    ax.set_ylabel("y", fontsize=11) # plota o rótulo do eixo y como y
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True) # mostra as linhas dos eixos à esquerda e embaixo, os marcadores de espaço e valores para entender a escala
    plt.tight_layout() # ajusta os espaçamentos na imagem para que nada fique cortado
    plt.show() # execução final, abre a janela e mostra o mapa completo

#  EXECUÇÃO (rodar apenas uma vez)

print("=" * 55)
print("  Criando malha 30×30...")
print("=" * 55)

G, grade_ids, saborexpress_no = criar_cidade()
salvar_cidade(G, grade_ids, saborexpress_no)
visualizar_cidade(G, saborexpress_no)

# após fechar o mapa mostra na saída a estrutura da cidade, quantidade de nós, posição da empresa e quantas arestas tem
print(f"\n  Estrutura da cidade:")
print(f"    Nós (cruzamentos): {G.number_of_nodes() - 1}")
print(f"    Sabor Express:     1  → pos={G.nodes[saborexpress_no]['pos']}")
print(f"    Total de nós:      {G.number_of_nodes()}")
print(f"    Arestas (ruas):    {G.number_of_edges()}")
print(f"    Grafo conexo:      {nx.is_connected(G)}")