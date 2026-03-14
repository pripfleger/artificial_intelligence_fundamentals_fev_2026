# ARQUIVO PARA CRIAÇÃO DA CIDADE E MAPA
# Empresa Sabor Express é um ponto fixo
# Execute apenas UMA VEZ
# Para alterar é só editar as constantes e rodar novamente.

import numpy as np # faz cálculos numéricos e geração de coordenadas aleatórias
import random # gera aleatoriedade na criação do grafo
import pickle # salvar/carregar o grafo em arquivo
import matplotlib.pyplot as plt # gera o desenho do mapa
import matplotlib.patches as mpatches # gera os itens coloridos do mapa
import networkx as nx # cria e manipula o grafo

SEED_CIDADE      = 42 # gera uma sequencia específica de números, representando sempre a mesma cidade, se alterar, altera a cidade.
GRADE            = 30 # tamanho da cidade como uma malha de 30x30
ESPACAMENTO_BASE = 10 # distância base entre cruzamentos
VARIACAO         = 0.25 # variação de ±25% no espaçamento
SABOR_EXPRESS    = (120, 85) # coordenada fixa do ponto de partida para as entregas
MAPA_CIDADE   = "mapacidade.pkl" # arquivo do mapa da cidade
PERC_MAO_UNICA   = 0.20 # 20% das ruas são mão única
PERC_NO_CARGA    = 0.20 # 20% dos nós centrais proibidos para carga
ESCOLAS_POS  = [(60, 60), (200, 200)] # posição das duas escolas
HOSPITAL_POS = (120, 160) # posição do hospital

# FUNÇÃO PARA CRIAR A CIDADE
def criar_cidade():
    random.seed(SEED_CIDADE) # fixa o random, usado para gerar as posições (x, y) dos nós, garantindo que o mapa não mude
    np.random.seed(SEED_CIDADE) # fixa o numpy, usado pra cálculos, ambos garantem que os nós do mapa sejam sempre os mesmos

    G = nx.Graph() # gera um grafo dirigido em branco (permite fazer direção única para simular rua de mão única)

    def gerar_posicoes(n): # gera n posições a partir de 0, com espaçamentos variáveis, para parecer um pouco mais real
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
            G.add_node(id_no, pos=(x, y), tipo="cruzamento", label=f"N{id_no}", grade=(linha, col), proibido_carga=False) # adiciona os nós no mapa e identifica como cruzamento pois são as intersecções das linhas/colunas
            grade_ids[linha][col] = id_no
            id_no += 1

    # Cria as arestas horizontais e verticais a partir de nós vizinhos
    arestas_base = [] # lista das arestas bidirecionais possiveis
    for linha in range(GRADE):
        for col in range(GRADE):
            no = grade_ids[linha][col]
            x1, y1 = G.nodes[no]["pos"]

            # vizinho à direita
            if col + 1 < GRADE: # fazer com que seja menor que a grade evita que passe do limite desejado da malha
                viz = grade_ids[linha][col + 1]
                x2, y2 = G.nodes[viz]["pos"]
                peso = round(np.sqrt((x2-x1)**2 + (y2-y1)**2), 2) # o peso é a distância euclidiana entre os dois nós
                arestas_base.append((no, viz, peso, "horizontal"))

            # vizinho acima
            if linha + 1 < GRADE:
                viz = grade_ids[linha + 1][col]
                x2, y2 = G.nodes[viz]["pos"]
                peso = round(np.sqrt((x2-x1)**2 + (y2-y1)**2), 2)
                arestas_base.append((no, viz, peso, "vertical"))

    # Define 20% das arestas como mão única fixo no mapa usando seed
    random.seed(SEED_CIDADE + 1)
    n_mao_unica = int(len(arestas_base) * PERC_MAO_UNICA) # calcula a quantidade de arestas que serão mão única
    indices_mao_unica = set(random.sample(range(len(arestas_base)), n_mao_unica)) # sorteia os índices das arestas que serão mão única
    arestas_mao_unica = set()  # guarda (u,v) que são mão única
 
    for idx, (u, v, peso, direcao) in enumerate(arestas_base):
        if idx in indices_mao_unica: # se o índice estiver entre os sorteados, será adicionado ao conjunto de arestas de mão única
            G.add_edge(u, v, weight=peso, mao_unica=True, bloqueada=False, velocidade=50, tipo_restricao="normal")
            arestas_mao_unica.add((u, v)) # apenas u→v
        else: # se não faz parte do sorteio, será mão dupla, e a aresta é adicionada para os dois sentidos
            G.add_edge(u, v, weight=peso, mao_unica=False, bloqueada=False, velocidade=50, tipo_restricao="normal") # sentido u→v
            G.add_edge(v, u, weight=peso, mao_unica=False, bloqueada=False, velocidade=50, tipo_restricao="normal") # sentido v→u

    # Marca o nó mais próximo da coordenada definida do SABOR_EXPRESS, como ponto fixo no mapa
    sx, sy = SABOR_EXPRESS
    saborexpress_no = min(G.nodes, key=lambda n: np.sqrt((G.nodes[n]["pos"][0] - sx)**2 + (G.nodes[n]["pos"][1] - sy)**2)) # calcula a menor distância euclidiana (baseado no teorema de pitágoras)
    G.nodes[saborexpress_no]["tipo"]  = "sabor_express" # define o tipo do nó
    G.nodes[saborexpress_no]["label"] = "SE" # define o rótulo para identificar o nó
    print(f"  Sabor Express → nó {saborexpress_no}  pos={G.nodes[saborexpress_no]["pos"]}") # mostra na saída as coordenadas ajustadas da Empresa.

    # Marca os nós mais próximos da coordenada definida para as escolas, como pontos fixos no mapa
    escolas_nos = [] # cria uma lista para guardar os nós que serão as duas escolas
    for epos in ESCOLAS_POS:
        ex, ey = epos
        no_escola = min(G.nodes, key=lambda n: np.sqrt((G.nodes[n]["pos"][0] - ex)**2 + (G.nodes[n]["pos"][1] - ey)**2))
        G.nodes[no_escola]["tipo"]  = "escola"
        G.nodes[no_escola]["label"] = "ESC"
        escolas_nos.append(no_escola)
        print(f"  Escola → nó {no_escola}  pos={G.nodes[no_escola]["pos"]}")

    # Marca o nó mais próximo da coordenada definida para o hospital, como ponto fixo no mapa
    hx, hy = HOSPITAL_POS
    hospital_no = min(G.nodes, key=lambda n: np.sqrt((G.nodes[n]["pos"][0] - hx)**2 + (G.nodes[n]["pos"][1] - hy)**2))
    G.nodes[hospital_no]["tipo"]  = "hospital"
    G.nodes[hospital_no]["label"] = "HOSP"
    print(f"  Hospital → nó {hospital_no}  pos={G.nodes[hospital_no]["pos"]}")

    nos_velocidade_reduzida = set() # define um conjunto para armazenar os nós com velocidade reduzida
    
    # Aplica velocidade reduzida de 30 km/h nas arestas vizinhas ao nó central
    def aplicar_velocidade_reduzida(no_central):
        viz_diretos = set(nx.neighbors(G, no_central)) # define o conjuntos dos nós vizinhos ao nó central escolhido
        for u, v, dados in G.edges(data=True): # se as coordenadas estiverem no conjunto vizinhos diretos, ou forem parte do nó central, marca velocidade de 30 e restrição do tipo lenta
            if u in viz_diretos or v in viz_diretos or u == no_central or v == no_central:
                G[u][v]["velocidade"] = 30
                G[u][v]["tipo_restricao"] = "zona_lenta"
                nos_velocidade_reduzida.add(u) # adiciona a coordenada u no conjunto de velocidade reduzida
                nos_velocidade_reduzida.add(v) # adiciona a coordenada v no conjunto de velocidade reduzida
 
    for no_escola in escolas_nos: # para cada nó de escola, aplica a função de redução de velocidade
        aplicar_velocidade_reduzida(no_escola)
    aplicar_velocidade_reduzida(hospital_no) # para o nó hospital aplica a função de redução de velocidade

    # Nós de 20% da parte central do mapa, proibidos para carga, área fixa
    todas_pos = np.array([G.nodes[n]["pos"] for n in G.nodes]) # cria uma lista em estrutura numpy ("empilhados"), permitindo que façamos operações diretas por coluna
    x_min, x_max = todas_pos[:, 0].min(), todas_pos[:, 0].max() # pega o menor e o maior valor de x na coluna 0 (limites horizontais do mapa)
    y_min, y_max = todas_pos[:, 1].min(), todas_pos[:, 1].max() # pega o menor e maior valor de y na coluna 1 (limites verticais do mapa)
    x_25, x_75 = x_min + 0.25*(x_max-x_min), x_min + 0.75*(x_max-x_min) # pega os limites centrais em x considerando 25% e 75% do mapa
    y_25, y_75 = y_min + 0.25*(y_max-y_min), y_min + 0.75*(y_max-y_min) # pega os limites centrais em y considerando 25% e 75% do mapa
 
    nos_centrais = [n for n in G.nodes if x_25 <= G.nodes[n]["pos"][0] <= x_75 and y_25 <= G.nodes[n]["pos"][1] <= y_75 and G.nodes[n]["tipo"] == "cruzamento"] # define os nós centrais considerando todos que sejam cruzamentos dentro da faixa definida acima
 
    # sorteia os 20% dos nós definidos como centrais, que serão marcados como proibidos para carga
    random.seed(SEED_CIDADE + 2)
    n_proibidos = int(len(nos_centrais) * PERC_NO_CARGA) # quantidade de nós centrais a serem sorteados
    nos_proibidos = set(random.sample(nos_centrais, n_proibidos)) # conjunto dos nós centrais sorteados
    for n in nos_proibidos: # marca de fato os nós sorteados como proibidos
        G.nodes[n]["proibido_carga"] = True
 
    print(f"  Nós proibidos para carga: {len(nos_proibidos)}") # mostra na saída a quantidade de nós proibidos

    info_restricoes = {
        "escolas_nos": escolas_nos,
        "hospital_no": hospital_no,
        "nos_velocidade_reduzida": nos_velocidade_reduzida,
        "nos_proibidos_carga": nos_proibidos,
        "arestas_mao_unica": arestas_mao_unica}

    return G, grade_ids, saborexpress_no, info_restricoes

# SALVA O GRAFO DA CIDADE EM UM ARQUIVO
def salvar_cidade(G, grade_ids, saborexpress_no, info_restricoes):
    with open(MAPA_CIDADE, "wb") as mapa: # vai abrir o arquivo e escrever nele em formato binário, se o arquivo já existir, irá sobrescrever
        pickle.dump({"grafo": G, "grade_ids": grade_ids, "saborexpress_no":  saborexpress_no, "info_restricoes": info_restricoes}, mapa)
    print(f"  Cidade salva em '{MAPA_CIDADE}'") # mostra na saída qual o nome do arquivo que tem o mapa salvo

# VISUAlIZAÇÃO DO MAPA
def visualizar_cidade(G, saborexpress_no, info_restricoes):
    escolas_nos = info_restricoes["escolas_nos"]
    hospital_no = info_restricoes["hospital_no"]
    nos_vel_reduzida = info_restricoes["nos_velocidade_reduzida"]
    nos_proib_carga = info_restricoes["nos_proibidos_carga"]

    fig, ax = plt.subplots(figsize=(18, 18)) # cria a janela com 18x18 polegadas e a área do mapa delimitada pelos eixos
    ax.set_facecolor("#f7f4ef") # define a cor de fundo do mapa
    fig.patch.set_facecolor("#f7f4ef") # define a cor de fundo da janela

    # ARESTAS (RUAS)
    desenhadas = set() # conjunto controle para não desenhar a mesma rua duas vezes, (u,v) e (v,u)
    for u, v, dados in G.edges(data=True): # percorre todas as arestas
        chave_bi = (min(u, v), max(u, v)) # cria uma chave única para cada aresta independente da direção
        xu, yu = G.nodes[u]["pos"] # pega as coordenadas x e y dos dois nós da aresta
        xv, yv = G.nodes[v]["pos"]
        
        mao_unica = dados.get("mao_unica", False) # verifica se a aresta tem o atributo "mao_unica" e se não tiver retorna False como padrão
        zona_lenta = dados.get("tipo_restricao") == "zona_lenta" # verifica se o atributo "tipo_restricao" da aresta é "zona_lenta" e retorna True ou False
 
        if mao_unica: # se for mão única
            cor = "#e67e22" # define a cor laranja para a "rua" mão única
            lw  = 1.4 # define a espessura da linha no mapa
            ax.annotate("", xy=(xv, yv), xytext=(xu, yu), arrowprops=dict(arrowstyle="->", color=cor, lw=1.5, mutation_scale=10), zorder=4) # desenha a aresta e uma seta laranja de u para v indicando direção da mão única

        elif zona_lenta: # se for zona lenta
            if chave_bi in desenhadas: # se já estiver no conjunto das desenhadas, ignora esta etapa e continua
                continue
            desenhadas.add(chave_bi) # se não estiver no conjunto, adiciona no conjunto
            cor = "#f1c40f" # define a cor amarelo para a "rua" em zona lenta
            lw  = 1.6 # define a espessura da linha no mapa
            ax.plot([xu, xv], [yu, yv], color=cor, linewidth=lw, zorder=2) # desenha a aresta
        else: # se não pertencer aos dois tipos acima (restante das arestas)
            if chave_bi in desenhadas: # ignora se já estiver desenhada
                continue
            desenhadas.add(chave_bi) # se não estiver desenhada, adiciona no conjunto
            cor = "#aaaaaa" # define a cor cinza
            lw  = 0.8 # define a espessura da linha no mapa
            ax.plot([xu, xv], [yu, yv], color=cor, linewidth=lw, zorder=1) # plota a aresta entre os nós

    # CRUZAMENTOS (NÓS)
    cruzamentos = [numero for numero, dict in G.nodes(data=True) if dict["tipo"] == "cruzamento" and not dict.get("proibido_carga")] # pega somente os nós definidos como tipo cruzamento e sem proibição de carga
    xc = [G.nodes[numero]["pos"][0] for numero in cruzamentos] # cria lista com os x de cada cruzamento (nó)
    yc = [G.nodes[numero]["pos"][1] for numero in cruzamentos] # cria lista com os y de cada cruzamento (nó)
    ax.scatter(xc, yc, color="#2c3e50", s=10, zorder=2) # "distribui" os nós no mapa

    # CRUZAMENTOS PROIBIDOS PARA CARGA
    xp = [G.nodes[n]["pos"][0] for n in nos_proib_carga]
    yp = [G.nodes[n]["pos"][1] for n in nos_proib_carga]
    ax.scatter(xp, yp, color="#8e44ad", s=18, marker="s", zorder=3, label="Proibido carga")

    # ZONAS VELOCIDADE REDUZIDA
    xvr = [G.nodes[n]["pos"][0] for n in nos_vel_reduzida]
    yvr = [G.nodes[n]["pos"][1] for n in nos_vel_reduzida]
    ax.scatter(xvr, yvr, color="#f1c40f", s=60, alpha=0.18, zorder=2)

    # ESCOLAS
    for no_escola in escolas_nos: # para cada escola
            xe, ye = G.nodes[no_escola]["pos"] # pega o x e y de cada escola
            ax.scatter(xe, ye, color="#3498db", s=250, marker="s", zorder=6) # coloca no mapa o ponto de cada escola
            ax.annotate("Escola", (xe, ye), textcoords="offset points", xytext=(8, 8), fontsize=9, fontweight="bold", color="#3498db", bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#3498db", alpha=0.9)) # adiciona rótulo para identificar as escolas

    # HOSPITAL
    xh, yh = G.nodes[hospital_no]["pos"] # pega as coordenadas x e y do hospital
    ax.scatter(xh, yh, color="#e74c3c", s=350, marker="P", zorder=6) # marca no mapa o hospital
    ax.annotate("Hospital", (xh, yh), textcoords="offset points", xytext=(8, 8), fontsize=9, fontweight="bold", color="#e74c3c", bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e74c3c", alpha=0.9)) # adiciona rótulo para identificar o hopital no mapa

    # EMPRESA (Sabor Express)
    xse, yse = G.nodes[saborexpress_no]["pos"] # pega as coordenadas da empresa
    ax.scatter(xse, yse, color="#27ae60", s=300, marker="*", zorder=7) # plota o nó que representa a empresa em formato de estrela
    ax.annotate("Sabor Express", (xse, yse), textcoords="offset points", xytext=(8, 8), fontsize=10, fontweight="bold", color="#27ae60", bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#27ae60", alpha=0.9)) # plota o nome da empresa próximo do nó
    
    # LEGENDA
    legenda = [mpatches.Patch(color="#27ae60", label="Sabor Express"),
               mpatches.Patch(color="#aaaaaa", label="Rua normal (mão dupla)"),
               mpatches.Patch(color="#e67e22", label=f"Mão única ↗"),
               mpatches.Patch(color="#f1c40f", label="Zona 30 km/h (escola/hospital)"),
               mpatches.Patch(color="#8e44ad", label="Proibido carga"),
               mpatches.Patch(color="#3498db", label="Escola"),
               mpatches.Patch(color="#e74c3c", label="Hospital")] # define os itens da legenda
    ax.legend(handles=legenda, loc="upper left", fontsize=9, facecolor="white", framealpha=0.95) # define características e posição da legenda no mapa
    ax.set_title("Mapa da Cidade — Malha 30×30", fontsize=14, fontweight="bold", pad=15) # plota o título do mapa
    ax.set_xlabel("x", fontsize=11) # plota o rótulo do eixo x como x
    ax.set_ylabel("y", fontsize=11) # plota o rótulo do eixo y como y
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True) # mostra as linhas dos eixos à esquerda e embaixo, os marcadores de espaço e valores para entender a escala
    plt.tight_layout() # ajusta os espaçamentos na imagem para que nada fique cortado
    plt.show() # execução final, abre a janela e mostra o mapa completo

#  EXECUÇÃO (rodar apenas uma vez)
print("=" * 60)
print("  Criando malha 30×30...")
print("=" * 60)

G, grade_ids, saborexpress_no, info_restricoes = criar_cidade()
salvar_cidade(G, grade_ids, saborexpress_no, info_restricoes)
visualizar_cidade(G, saborexpress_no, info_restricoes)

# após fechar o mapa mostra na saída a estrutura da cidade, quantidade de nós, posição da empresa e quantas arestas tem
print(f"\n  Estrutura da cidade:")
print(f"    Nós (cruzamentos): {G.number_of_nodes() - 1 - len(info_restricoes['escolas_nos']) - 1}")
print(f"    Escolas:           {len(info_restricoes['escolas_nos'])}")
print(f"    Hospital:          1")
print(f"    Sabor Express:     1  → pos={G.nodes[saborexpress_no]['pos']}")
print(f"    Total de nós:      {G.number_of_nodes()}")
print(f"    Arestas (ruas):    {G.number_of_edges()}")
print(f"    Mão única:         {sum(1 for u,v,d in G.edges(data=True) if d.get('mao_unica'))}")
print(f"    Zona 30 km/h:      {sum(1 for u,v,d in G.edges(data=True) if d.get('tipo_restricao')=='zona_lenta')}")
print(f"    Proibido carga:    {len(info_restricoes['nos_proibidos_carga'])} nós")