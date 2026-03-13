# ARQUIVO PARA GERAR ROTA INTELIGENTE (calcula da saída até a chegada)
# Agrupa por proximidade (K-Means) e usa o A* para calcular a menor distância entre cada par de pontos
# Cada nova rodada gera entregas diferentes pela aleatorização das entregas

import numpy as np # faz cálculos numéricos e geração de coordenadas aleatórias
import random # gera aleatoriedade na criação do grafo
import heapq # gera a fila de prioridade que o A* utiliza no início
import pickle # salvar/carregar o grafo em arquivo
import matplotlib.pyplot as plt # gera o desenho do mapa
import matplotlib.patches as mpatches # gera os itens coloridos do mapa
import networkx as nx # cria e manipula o grafo
from sklearn.cluster import KMeans # algorítmo que faz o clustering dos pontos por proximidade

MAPA_CIDADE = 'mapacidade.pkl'

# Lista de cores que os grupos podem receber no mapa
CORES_GRUPOS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#00bcd4']

#  FUNÇÃO QUE CARREGA A CIDADE
def carregar_cidade():
    with open(MAPA_CIDADE, 'rb') as f: # abre o arquivo no modo leitura binária com o alias "f"
        dados = pickle.load(f)
    G = dados['grafo'] # recupera o grafo, a grade e o ID da empresa (ponto fixo)
    grade_ids = dados['grade_ids']
    saborexpress_no = dados['saborexpress_no']

    print(f"  Cidade carregada de '{MAPA_CIDADE}'")
    print(f"  Nós: {G.number_of_nodes()}  |  Arestas: {G.number_of_edges()}")
    print(f"  Sabor Express → nó {saborexpress_no}  pos={G.nodes[saborexpress_no]['pos']}")
    return G, grade_ids, saborexpress_no

#  FUNÇÕES AUXILIARES
# ================================================================

def heuristica(G, no_atual, no_destino):
    """
    h(n) = distância euclidiana entre no_atual e no_destino.
    Admissível: nunca superestima o custo real → garante
    que o A* sempre encontra o caminho ótimo.
    """
    x1, y1 = G.nodes[no_atual]['pos']
    x2, y2 = G.nodes[no_destino]['pos']
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def distancia_euclidiana(G, u, v):
    """Distância direta entre dois nós — usada para ordenar entregas."""
    x1, y1 = G.nodes[u]['pos']
    x2, y2 = G.nodes[v]['pos']
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)


# ================================================================
#  ALGORITMO A*
# ================================================================

def astar(G, origem, destino):
    """
    Calcula o caminho de menor custo entre origem e destino.

      g(n) = custo real acumulado desde a origem até n
      h(n) = heurística (distância euclidiana até o destino)
      f(n) = g(n) + h(n) → prioridade na fila

    Retorna:
      caminho: lista de nós do origem ao destino
      custo:   custo total do caminho
    """
    heap     = []
    heapq.heappush(heap, (0, 0, origem))
    g        = {origem: 0}
    veio_de  = {origem: None}
    visitados = set()

    while heap:
        f, custo_atual, no = heapq.heappop(heap)

        if no == destino:
            caminho = []
            while no is not None:
                caminho.append(no)
                no = veio_de[no]
            caminho.reverse()
            return caminho, custo_atual

        if no in visitados:
            continue
        visitados.add(no)

        for vizinho, dados_aresta in G[no].items():
            if vizinho in visitados:
                continue
            peso   = dados_aresta.get('weight', 1)
            g_novo = custo_atual + peso
            h_novo = heuristica(G, vizinho, destino)
            f_novo = g_novo + h_novo
            if vizinho not in g or g_novo < g[vizinho]:
                g[vizinho]       = g_novo
                veio_de[vizinho] = no
                heapq.heappush(heap, (f_novo, g_novo, vizinho))

    return [], float('inf')


# ================================================================
#  GERAÇÃO DE ENTREGAS
# ================================================================

def gerar_entregas(G, sabor_no):
    """
    Sorteia entre 1 e 10 nós aleatórios como pontos de entrega.
    Nunca sorteia o Sabor Express.
    Cada execução gera entregas diferentes.
    """
    disponiveis = [n for n in G.nodes if n != sabor_no]
    quantidade  = random.randint(1, min(10, len(disponiveis)))
    entregas    = random.sample(disponiveis, k=quantidade)

    print(f"\n{'='*55}")
    print(f"  {quantidade} entrega(s) gerada(s)")
    print(f"{'='*55}")
    for e in entregas:
        print(f"  Nó {e:5d}  pos={G.nodes[e]['pos']}")

    return entregas


# ================================================================
#  AGRUPAMENTO K-MEANS
# ================================================================

def agrupar_entregas(G, entregas):
    """
    Agrupa as entregas por proximidade geográfica usando K-Means.
    K = raiz quadrada do número de entregas (mínimo 1).
    Pontos isolados são absorvidos pelo grupo mais próximo.
    """
    if len(entregas) == 1:
        print(f"\n  1 entrega — sem agrupamento necessário.")
        return {0: entregas}

    coords  = np.array([G.nodes[e]['pos'] for e in entregas])
    k       = max(1, round(np.sqrt(len(entregas))))
    k       = min(k, len(entregas))

    kmeans  = KMeans(n_clusters=k, n_init=10)
    kmeans.fit(coords)
    rotulos = kmeans.labels_

    grupos = {}
    for idx, no in enumerate(entregas):
        gid = int(rotulos[idx])
        grupos.setdefault(gid, []).append(no)

    print(f"\n  K-Means → {k} grupo(s):")
    for gid, nos in grupos.items():
        print(f"    Grupo {gid}: {nos}")

    return grupos


# ================================================================
#  ORDEM DOS GRUPOS (aleatória)
# ================================================================

def ordenar_grupos(grupos):
    ids = list(grupos.keys())
    random.shuffle(ids)
    print(f"\n  Ordem dos grupos: {ids}")
    return ids


# ================================================================
#  MONTA SEQUÊNCIA DE VISITA
# ================================================================

def montar_sequencia(G, sabor_no, grupos, ordem_grupos):
    """
    Sabor Express → grupo0 → grupo1 → ... → Sabor Express
    Dentro de cada grupo: visita o mais próximo do último ponto.
    """
    sequencia = [sabor_no]
    ultimo    = sabor_no

    for gid in ordem_grupos:
        restantes = list(grupos[gid])
        while restantes:
            proximo = min(restantes,
                          key=lambda n: distancia_euclidiana(G, ultimo, n))
            sequencia.append(proximo)
            ultimo = proximo
            restantes.remove(proximo)

    sequencia.append(sabor_no)

    print(f"\n  Sequência ({len(sequencia)} pontos):")
    print(f"    {' → '.join(str(n) for n in sequencia)}")

    return sequencia


# ================================================================
#  CALCULA ROTA COMPLETA COM A*
# ================================================================

def calcular_rota_astar(G, sequencia):
    """
    Executa A* entre cada par consecutivo da sequência
    e concatena os caminhos em uma rota contínua pelas ruas reais.
    """
    rota_completa = []
    custo_total   = 0

    print(f"\n  Calculando rotas com A*...")

    for i in range(len(sequencia) - 1):
        origem  = sequencia[i]
        destino = sequencia[i + 1]

        caminho, custo = astar(G, origem, destino)

        if not caminho:
            print(f"  ⚠ Sem caminho entre nó {origem} e nó {destino}!")
            continue

        print(f"    {origem:5d} → {destino:5d}  "
              f"| {len(caminho)-1} passos  | custo={custo:.2f}")

        if rota_completa:
            rota_completa += caminho[1:]
        else:
            rota_completa += caminho

        custo_total += custo

    print(f"\n  Custo total: {custo_total:.2f}")
    print(f"  Nós percorridos: {len(rota_completa)}")

    return rota_completa, custo_total


# ================================================================
#  VISUALIZAÇÃO
# ================================================================

def visualizar_rota(G, sabor_no, grupos, rota_completa,
                    sequencia, custo_total):
    fig, ax = plt.subplots(figsize=(16, 16))
    ax.set_facecolor('#f7f4ef')
    fig.patch.set_facecolor('#f7f4ef')

    # Todas as arestas da cidade
    for u, v in G.edges():
        xu, yu = G.nodes[u]['pos']
        xv, yv = G.nodes[v]['pos']
        ax.plot([xu, xv], [yu, yv],
                color='#cccccc', linewidth=0.6, zorder=1)

    # Todos os nós
    xc = [G.nodes[n]['pos'][0] for n in G.nodes if n != sabor_no]
    yc = [G.nodes[n]['pos'][1] for n in G.nodes if n != sabor_no]
    ax.scatter(xc, yc, c='#dce0e0', s=6, zorder=2)

    # Rota calculada pelo A*
    for i in range(len(rota_completa) - 1):
        u, v   = rota_completa[i], rota_completa[i + 1]
        xu, yu = G.nodes[u]['pos']
        xv, yv = G.nodes[v]['pos']
        ax.plot([xu, xv], [yu, yv],
                color='#e74c3c', linewidth=2.0, zorder=3, alpha=0.8)

    # Pontos de entrega coloridos por grupo
    for gid, nos_grupo in grupos.items():
        cor = CORES_GRUPOS[gid % len(CORES_GRUPOS)]
        for n in nos_grupo:
            x, y = G.nodes[n]['pos']
            ax.scatter(x, y, c=cor, s=120, marker='o',
                       zorder=5, edgecolors='white', linewidths=1.2)

    # Numeração da ordem de visita
    for ordem, no in enumerate(sequencia):
        if no == sabor_no:
            continue
        x, y = G.nodes[no]['pos']
        ax.annotate(str(ordem), (x, y),
                    textcoords="offset points", xytext=(6, 6),
                    fontsize=8, fontweight='bold', color='#2c3e50',
                    bbox=dict(boxstyle='round,pad=0.25',
                              fc='white', ec='#cccccc', alpha=0.9))

    # Sabor Express
    xse, yse = G.nodes[sabor_no]['pos']
    ax.scatter(xse, yse, c='#27ae60', s=400, marker='*', zorder=6)
    ax.annotate('Sabor Express', (xse, yse),
                textcoords="offset points", xytext=(8, 8),
                fontsize=10, fontweight='bold', color='#27ae60',
                bbox=dict(boxstyle='round,pad=0.3',
                          fc='white', ec='#27ae60', alpha=0.9))

    # Legenda
    legenda = [
        mpatches.Patch(color='#27ae60', label='Sabor Express'),
        mpatches.Patch(color='#e74c3c',
                       label=f'Rota A* (custo total={custo_total:.2f})')
    ]
    for gid, nos_grupo in grupos.items():
        legenda.append(mpatches.Patch(
            color=CORES_GRUPOS[gid % len(CORES_GRUPOS)],
            label=f"Grupo {gid}: {nos_grupo}"
        ))

    ax.legend(handles=legenda, loc='upper right', fontsize=9,
              facecolor='white', framealpha=0.95)
    ax.set_title(f"Rota A* — {sum(len(v) for v in grupos.values())} entregas  |  "
                 f"{len(grupos)} grupo(s)  |  custo total={custo_total:.2f}",
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("x", fontsize=11)
    ax.set_ylabel("y", fontsize=11)
    ax.tick_params(left=True, bottom=True,
                   labelleft=True, labelbottom=True)
    plt.tight_layout()
    plt.show()


# ================================================================
#  EXECUÇÃO
# ================================================================

if __name__ == '__main__':

    G, grade_ids, saborexpress_no = carregar_cidade()

    entregas     = gerar_entregas(G, saborexpress_no)
    grupos       = agrupar_entregas(G, entregas)
    ordem_grupos = ordenar_grupos(grupos)
    sequencia    = montar_sequencia(G, saborexpress_no, grupos, ordem_grupos)

    rota_completa, custo_total = calcular_rota_astar(G, sequencia)

    visualizar_rota(G, saborexpress_no, grupos, rota_completa,
                    sequencia, custo_total)

    print(f"\n{'='*55}")
    print(f"  Resumo")
    print(f"{'='*55}")
    print(f"  Entregas:        {len(entregas)}")
    print(f"  Grupos:          {len(grupos)}")
    print(f"  Custo total:     {custo_total:.2f}")
    print(f"  Nós percorridos: {len(rota_completa)}")