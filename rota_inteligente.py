# ARQUIVO PARA GERAR ROTA INTELIGENTE, CONSIDERANDO RESTRIÇÕES NA CIDADE, DE IDA E VOLTA (com múltiplos entregadores)
# Cada rodada gera de 10 a 50 entregas divididas entre até 5 entregadores (máx 10 cada)
# Agrupa entregas por proximidade (K-Means) e usa o A* para calcular a menor distância entre cada par de pontos
# Cada nova rodada gera entregas diferentes pela aleatorização das entregas

import numpy as np # faz cálculos numéricos e geração de coordenadas aleatórias
import random # gera aleatoriedade na criação do grafo
import heapq # gera a fila de prioridade que o A* utiliza no início
import pickle # salvar/carregar o grafo em arquivo
import matplotlib.pyplot as plt # gera o desenho do mapa
import matplotlib.patches as mpatches # gera os itens coloridos do mapa
import networkx as nx # cria e manipula o grafo
from sklearn.cluster import KMeans # algorítmo que faz o clustering dos pontos por proximidade

MAPA_CIDADE = "mapacidade.pkl"
MAX_ENTREGADORES = 5 # não usa mais do que 5 entregadores
MAX_ENTREGAS_POR = 10 # máximo de entregas por entregador
MIN_SORT_ENTREGAS = 10 # sorteia no mínimo 10 entregas por rodada
MAX_SORT_ENTREGAS = 50 # sorteia no máximo 50 entregas por rodada

# Lista de cores que os grupos de entregas podem receber no mapa, para cada entregador
CORES_ENTREGADORES = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]

# Tipos de bloqueio e características
TIPOS_BLOQUEIO = {"obras": {"cor": "#e67e22", "hatch": "///", "label": "Bloqueio - Obras"}, "acidente": {"cor": "#e74c3c", "hatch": "xxx", "label": "Bloqueio - Acidente"}}

#  FUNÇÃO QUE CARREGA A CIDADE
def carregar_cidade():
    with open(MAPA_CIDADE, "rb") as f: # abre o arquivo no modo leitura binária com o alias "f"
        dados = pickle.load(f)
    G = dados["grafo"] # recupera o grafo, a grade e o ID da empresa (ponto fixo)
    grade_ids = dados["grade_ids"]
    saborexpress_no = dados["saborexpress_no"]
    info_restricoes = dados.get("info_restricoes", {})

    return G, grade_ids, saborexpress_no, info_restricoes

# FUNÇÃO DE GERAR BLOQUEIOS ALEATÓRIOS
def aplicar_bloqueios(G, saborexpress_no): # Bloqueia 3 ruas por obras e 2 por acidente, aleatoriamente
    # Candidatas: arestas que não saem/chegam ao Sabor Express
    candidatas = [(u, v) for u, v in G.edges() if u != saborexpress_no and v != saborexpress_no and not G[u][v].get("bloqueada", False)] # arestas que não são próximas a empresa e não foram bloqueadas
    random.shuffle(candidatas) # embaralha a lista para sorteio
    bloqueios = [] # lista que vai guardar os bloqueios
    for u, v in candidatas[:3]: # pega as 3 primeiras aerestas da lista embaralhada e define bloqueio por obras
        G[u][v]["bloqueada"] = True
        G[u][v]["tipo_bloqueio"] = "obras"
        bloqueios.append((u, v, "obras")) # adiciona na lista de bloqueios
    for u, v in candidatas[3:5]: # pega a terceira e quarta arestas e define bloqueio por acidente
        G[u][v]["bloqueada"] = True
        G[u][v]["tipo_bloqueio"] = "acidente"
        bloqueios.append((u, v, "acidente")) # adiciona na lista de bloqueios
    return bloqueios # retorna a lista com os bloqueios aplicados da rodada

#  HEURÍSTICA (MÉTODO USADO PARA RESOLVER PROBLEMAS COMPLEXOS APESAR DE NÃO GARANTIR A MELHOR RESPOSTA)
def heuristica(G, no_atual, no_destino): # h(n) = distância euclidiana (hipotenusa - teorema de pitágoras) entre nó atual e o destino, admissível
    x1, y1 = G.nodes[no_atual]["pos"]
    x2, y2 = G.nodes[no_destino]["pos"]
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2) # retorna o valor da distância euclidiana entre o nó atual e o destino

def custo_aresta(G, u, v): # custo real da aresta u→v, considerando: bloqueios, rua bloqueada: infinito, zona lenta: peso * fator de penalidade (1.8), normal: peso direto
    dados = G[u][v]
    if dados.get("bloqueada", False):
        return float("inf") # se a rua for bloqueada e não pode passar, retorna infinito
    peso = dados.get("weight", 1) # atribui peso 1 como padrão
    if dados.get("tipo_restricao") == "zona_lenta": # se os dados forem de zona lenta
        return peso * 1.8   # atribui penalidade por velocidade reduzida, aumentando o peso da aresta
    return peso # aresta normal retorna peso direto sem penalidade

def distancia_euclidiana(G, u, v): # distância euclidiana entre dois nós — usada para ordenar entregas - usada no nearest neighbor
    x1, y1 = G.nodes[u]["pos"]
    x2, y2 = G.nodes[v]["pos"]
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2) # retorna o valor da distância euclidiana entre u e v

#  ALGORITMO A*
def astar(G, origem, destino): # calcula o caminho de menor custo entre origem e destino 
    heap = [] # cria fila de prioridade vazia, cada item da fila é (f, custo_acumulado, nó)
    heapq.heappush(heap, (0, 0, origem)) # insere a origem com custo 0 e f = 0
    g = {origem: 0} # dicionário que guarda menor custo conhecido até cada um dos nós, começando pela origem
    veio_de  = {origem: None} # guarda de qual nó veio para chegar ao nó visitado
    visitados = set() # guarda os nós já visitados evitando repetir nós já visitados

    while heap:
        f, custo_atual, no = heapq.heappop(heap) # enquanto tem nó na fila, pega o de menor f (custo + heurística) e já exclui da fila
        
        if no == destino: # se o nó for o de destino
            caminho = [] # lista vazia do caminho
            while no is not None: # enquanto o nó não for nenhum
                caminho.append(no) # adiciona na lista do caminho o nó e de onde veio
                no = veio_de[no]
            caminho.reverse() # reverte a lista pra deixar na ordem de origem → destino
            return caminho, custo_atual # retorna o caminho e o custo atual total

        if no in visitados: # se o nó já foi visitado, continua
            continue
        visitados.add(no) # se não foi visitado, adiciona no conjunto dos visitados

        for vizinho in G.successors(no): # para cada vizinho do nó atual, respeitando a direção das arestas
            if vizinho in visitados: # se o vizinho já foi visitado, continua
                continue
            c = custo_aresta(G, no, vizinho) # calcula o peso da aresta, pode ser infinito ou ter penalidade por restrição
            if c == float("inf"): # se o peso for infinito ignora esse caminho
                continue
            g_novo = custo_atual + c # calcula o novo g, custo acumulado até o vizinho
            h_novo = heuristica(G, vizinho, destino) # calcula a heurística do vizinho até o destino
            f_novo = g_novo + h_novo # valor vai determinar a prioridade na fila
            if vizinho not in g or g_novo < g[vizinho]: # se o vizinho não estiver no dicionário g ou o g_novo for menor que o g do vizinho
                g[vizinho] = g_novo # atuaiza o g para ficar com o menor
                veio_de[vizinho] = no # registra de onde veio
                heapq.heappush(heap, (f_novo, g_novo, vizinho)) # insere na fila com nova prioridade

    return [], float("inf") # se o loop terminar sem achar destino retorna caminho vazio com custo infinito

#  GERAÇÃO DE ENTREGAS
def gerar_entregas(G, sabor_no): #sorteia entre 1 e 10 nós aleatórios como pontos de entrega em cada rodada
    disponiveis = [n for n in G.nodes if n != sabor_no] # pontos de entrega disponíveis são qualquer um que não seja a empresa de origem
    quantidade = random.randint(MIN_SORT_ENTREGAS, min(MAX_SORT_ENTREGAS, len(disponiveis))) # sorteia quantas entregas serão feitas entre 10 e 50
    entregas = random.sample(disponiveis, k=quantidade) # sorteia os nós para entrega a partir da lista dos disponíveis de acordo com a quantidade sorteada de entregas

    return entregas # retorna lista dos nós de entrega

#  AGRUPAMENTO DAS ENTREGAS POR ENTREGADOR (K-MEANS)
def agrupar_entregas(G, entregas): # agrupa as entregas por proximidade usando K-Means considerando o máximo permitido por entregador
    n = len(entregas) # quantidade total de entregas
    k = min(MAX_ENTREGADORES, max(1, int(np.ceil(n / MAX_ENTREGAS_POR)))) # quantidade de entregadores necessária, arredondando para cima, sempre entre 1 e 5
    
    if n == 1: # se tiver somente 1 entrega, vai para o entregador 0
        return {0: entregas}

    coords = np.array([G.nodes[entrega]["pos"] for entrega in entregas]) # pega o x e y de cada ponto de entrega
    kmeans  = KMeans(n_clusters=k, n_init=10, random_state=0) # cria o KMeans com k grupos, roda 10 vezes e pega o melhor resultado
    kmeans.fit(coords) # faz o agrupamento das entregas, encontra o centróide e calcula os grupos ideais pela similaridade
    rotulos = kmeans.labels_ # mostra qual grupo ficou com qual entrega, onde cada posição corresponde a uma entrega e o valor é o número do grupo ao qual ela foi atribuída

    grupos = {} # cria o dicionário dos grupos
    for idx, no in enumerate(entregas): # para cada posição (id) da lista de entregas - x e y
        grupo_id = int(rotulos[idx]) # pega o grupo correspondente ao id (atribuído pelo KMeans)
        grupos.setdefault(grupo_id, []).append(no) # cria o grupo vazio se não existir ainda, e adiciona o nó ao seu grupo

    centros = kmeans.cluster_centers_ # centróides encontrados após aplicar KMeans nos pontos

    for grupo_id, nos in grupos.items(): # para cada grupo e seus nós
        cx, cy = centros[grupo_id] # pega as coordenadas do centróide
        grupos[grupo_id] = sorted(nos, key=lambda no: np.sqrt((G.nodes[no]["pos"][0] - cx)**2 + (G.nodes[no]["pos"][1] - cy)**2)) # ordena os nós pela distância do menor para o maior

    # FUNÇÃO DE BALANCEAMENTO CASO ALGUM GRUPO TENHA MAIS DE 10 ENTREGAS
    def grupo_mais_proximo_com_espaco(no_entrega, grupo_id_origem): # recebe o nó excedente e o grupo que veio
        xe, ye = G.nodes[no_entrega]["pos"] # pega as coordenadas do nó de entrega
        melhor_grupo, dist_melhor = None, float("inf") # guarda o grupo mais próximo encontrado e a menor distância encontrada começando com None e infinito
        for grupo_id, nos in grupos.items(): # para cada id do grupo e seu nó existente na lista de grupos
            if grupo_id == grupo_id_origem or len(nos) >= MAX_ENTREGAS_POR: # se o grupo de origem for o mesmo ou a quantidade for maior que 10, ignora o grupo
                continue
            cx, cy = centros[grupo_id] # pega as coordenadas do centróide do grupo
            d = np.sqrt((xe - cx)**2 + (ye - cy)**2) # calcula a distância do ponto excedente até esse centróide
            if d < dist_melhor: # se a distância calculada for menor que a que existia, atualiza como melhor distância e melhor grupo
                dist_melhor, melhor_grupo = d, grupo_id
        return melhor_grupo # retorna o grupo mais próximo que pode receber a entrega excedente
 
    for grupo_id in list(grupos.keys()): # para cada entrega do grupo, identificada pelo seu id
        while len(grupos[grupo_id]) > MAX_ENTREGAS_POR: # enquanto o grupo tiver mais de 10 entregas (ids)
            excesso = grupos[grupo_id].pop() # vai excluir a última entrega do grupo
            destino_grupo_id = grupo_mais_proximo_com_espaco(excesso, grupo_id) # define o grupo mais próximo encontrado pela função de balanceamento como grupo de destino
            if destino_grupo_id is None: # se o grupo de destino não existir, mantém o excesso no grupo original
                grupos[grupo_id].append(excesso)  # não há espaço; mantém
                break
            grupos[destino_grupo_id].append(excesso) # adiciona o excesso no grupo de destino

    return grupos # retorna o dicionário dos grupos

#  MONTA SEQUÊNCIA DE ENTREGA PARA CADA ENTREGADOR SAINDO DA EMPRESA E RETORNANDO AO FINAL
def montar_sequencia_entregador(G, sabor_no, nos_entrega):
    sequencia = [sabor_no] # começa pela empresa de onde todos os entregadores saem
    restantes = list(nos_entrega) # lista de entregas copiada para não modificar a original
    ultimo = sabor_no # último nó visitado, retorno à empresa

    while restantes: # enquanto tem entregas na lista
        proximo = min(restantes, key=lambda n: distancia_euclidiana(G, ultimo, n)) # encontra o nearest neighbor, a entrega mais próxima
        sequencia.append(proximo) # adiciona essa entrega na sequência
        ultimo = proximo # atualiza o último nó visitado
        restantes.remove(proximo) # remove o nó da lista de restantes

    sequencia.append(sabor_no) # no final adiciona a empresa para registrar o retorno do entregador

    return sequencia # retorna a sequência completa da rota do entregador

#  CALCULA ROTA COMPLETA COM A*
def calcular_rota_astar(G, sequencia): # executa A* entre cada par consecutivo da sequência
    rota_completa = [] # vai guardar todos os nós percorridos
    custo_total = 0 # vai acumular o custo dos trechos
    segmentos = [] # guarda cada trecho separado com [(origem, destino, caminho, custo)]

    for i in range(len(sequencia) - 1): # para cada index do par de nós consecutivos (origem, destino)
        origem  = sequencia[i] # pega a origem do par
        destino = sequencia[i + 1] # pega o destino do par

        caminho, custo = astar(G, origem, destino) # executa o A* e encontra o caminho e o custo do trecho

        if not caminho: # se não encontrar caminho, adiciona o segmento com caminho vazio e custo infinito e pula pro próximo par
            segmentos.append((origem, destino, [], float("inf")))
            continue
        segmentos.append((origem, destino, caminho, custo)) # adiciona o segmento com todos os dados

        if rota_completa: # se já tem nós na rota completa, vai adicionar o caminho sem o primeiro nó, pois foi o destino adicionado do trecho anterior, assim não duplica a junção dos nós
            rota_completa += caminho[1:]
        else:
            rota_completa += caminho # adiciona o caminho

        custo_total += custo # atualiza o custo total acumulando o último custo

    return rota_completa, custo_total, segmentos # retorna a rota completa, o custo total e os segmentos

#  VISUALIZAÇÃO
def visualizar_rota(G, sabor_no, info_restricoes, bloqueios, grupos, rotas_por_entregador, sequencias_por_entregador):

    escolas_nos = info_restricoes.get("escolas_nos", []) # extrai os dados das restrições para poder inserir no mapa
    hospital_no = info_restricoes.get("hospital_no")
    nos_vel_reduzida = info_restricoes.get("nos_velocidade_reduzida", set())
    nos_proib_carga = info_restricoes.get("nos_proibidos_carga", set())
    bloqueios_obras    = {(u, v) for u, v, tipo in bloqueios if tipo == "obras"} # separa os trechos de bloqueios em conjuntos por tipo de boqueio
    bloqueios_acidente = {(u, v) for u, v, tipo in bloqueios if tipo == "acidente"}

    fig, ax = plt.subplots(figsize=(20, 20)) # cria a janela do mapa de 20x20 polegadas
    ax.set_facecolor("#f7f4ef") # define as cores do fundo do mapa e da janela
    fig.patch.set_facecolor("#f7f4ef")

    desenhadas = set() # controle para não desenhar arestas duas vezes

    # Todas as arestas da cidade
    for u, v, dados in G.edges(data=True): # para todas as arestas e seus atributos
        xu, yu = G.nodes[u]["pos"] # pega as coordenadas x e y dos nós da aresta
        xv, yv = G.nodes[v]["pos"]
        chave_bi = (min(u, v), max(u, v)) # cria uma chave única independente da direção para poder desenhar as ruas de mão dupla uma vez só
        
        tem_bloqueio_obras = (u, v) in bloqueios_obras or (v, u) in bloqueios_obras # verifica se a aresta está bloqueada por obra nos dois sentidos
        tem_bloqueio_acidente = (u, v) in bloqueios_acidente or (v, u) in bloqueios_acidente # verifica se a aresta está bloqueada por acidente nos dois sentidos
        mao_unica = dados.get("mao_unica", False) # verifica se a aresta é do tipo mão única
        zona_lenta = dados.get("tipo_restricao") == "zona_lenta" # verifica se é do tipo zona lenta
 
        if tem_bloqueio_obras: # se for bloqueada por obra desenha aresta na cor do fundo para não aparecer e passa para a próxima aresta
            ax.plot([xu, xv], [yu, yv], color="#f7f4ef", linewidth=3.0, zorder=3, linestyle="--")
            continue
        if tem_bloqueio_acidente: # se for bloqueada por acidente desenha aresta da cor do fundo para não aparecer e passa para próxima aresta
            ax.plot([xu, xv], [yu, yv], color="#f7f4ef", linewidth=3.0, zorder=3, linestyle=":")
            continue
        if mao_unica: # se for mão única desenha seta laranja
            ax.annotate("", xy=(xv, yv), xytext=(xu, yu), arrowprops=dict(arrowstyle="->", color="#e67e22", lw=1.2, mutation_scale=8), zorder=4)
            continue
        if zona_lenta: # se for zona lenta desenha aresta em amarelo
            if chave_bi in desenhadas: # se já foi desenhada pula
                continue
            desenhadas.add(chave_bi) # se não foi desenhada marca como desenhada
            ax.plot([xu, xv], [yu, yv], color="#f1c40f", linewidth=1.4, zorder=2)
        else: # o restante das arestas pinta de azul escuro
            if chave_bi in desenhadas: # se já foi pintada pula para a próxima
                continue
            desenhadas.add(chave_bi)
            ax.plot([xu, xv], [yu, yv], color="#2d3561", linewidth=0.7, zorder=1)

    # Todos os cruzamentos
    for no, dados in G.nodes(data=True): # para cada nó e seus atributos
        if dados["tipo"] in ("sabor_express", "escola", "hospital"): # se for a empresa, escolas ou hospital, pula para o próximo
            continue
        x, y = dados["pos"] # pega o x e y do nó
        if dados.get("proibido_carga"): # se for área proibida para carga pesada desenha um quadrado roxo no nó
            ax.scatter(x, y, color="#8e44ad", s=20, marker="s", zorder=3)
        else: # outros cruzamentos desenha na cor azul escuro
            ax.scatter(x, y, color="#4a4a7a", s=5, zorder=2)

    # Rota dos entregadores
    for eid, rota in rotas_por_entregador.items(): # para cada id de entrega da rota de cada entregador 
        cor = CORES_ENTREGADORES[eid % len(CORES_ENTREGADORES)] # pega a cor do entregador pela posição na lista de cores
        for i in range(len(rota) - 1): # para cada par de nós consecutivos da rota
            u, v = rota[i], rota[i + 1] # pega os dois nós
            xu, yu = G.nodes[u]["pos"] # pega as coordenadas x e y de cada um dos nós
            xv, yv = G.nodes[v]["pos"]
            ax.plot([xu, xv], [yu, yv], color=cor, linewidth=2.5, zorder=5, alpha=0.85) # desenha a aresta da rota com a cor do enrtegador

    # Pontos de entrega por entregador
    for eid, nos_grupo in grupos.items(): # para cada entrega nos grupos
        cor = CORES_ENTREGADORES[eid % len(CORES_ENTREGADORES)] # pega a cor do entregador
        sequencia = sequencias_por_entregador[eid] # pega a sequência de entregas do entregador
        for ordem, no in enumerate(sequencia): # percorre os nós na ordem da sequência
            if no == sabor_no: # se for o nó da empresa pula para o próximo
                continue
            x, y = G.nodes[no]["pos"] # pega o x e y do nó e desenha um círculo da cor do entregador maior que os nós normais para destacar
            ax.scatter(x, y, c=cor, s=60, marker="o", zorder=6, edgecolors="black", linewidths=1.5)
            ax.annotate(str(ordem), (x, y), textcoords="offset points", xytext=(5, 5), fontsize=7, fontweight="bold", color="black", bbox=dict(boxstyle="round,pad=0.2", fc=cor, ec="none", alpha=0.85), zorder=7)
            
    # Bloqueios
    for u, v, tipo in bloqueios: # para cada aresta bloqueada
        if not G.has_node(u) or not G.has_node(v): # verifica se os nós dessa aresta existem
            continue
        xu, yu = G.nodes[u]["pos"] # pega os x e y de cada nó dessa aresta
        xv, yv = G.nodes[v]["pos"]
        mx, my = (xu + xv) / 2, (yu + yv) / 2 # calcula o ponto médio entre os dois nós
        cor_bloq = "#e67e22" if tipo == "obras" else "#ff1744"
        ax.scatter(mx, my, color=cor_bloq, s=70, marker="X", zorder=8, edgecolors="black", linewidths=1) # desenha no ponto médio o marcador de bloqueio na cor laranja para obras e vermelho para acidentes

    # Escolas
    for no_escola in escolas_nos: # para cada nó que representa escola
        xe, ye = G.nodes[no_escola]["pos"] # pega a posição da escola
        ax.scatter(xe, ye, color='#3498db', s=150, marker='s', zorder=8) # desenha um quadrado azul e a legenda próximo do ponto
 
    # Hospital
    if hospital_no is not None: # se o hispital existir
        xh, yh = G.nodes[hospital_no]["pos"] # pega a posição do hospital
        ax.scatter(xh, yh, color="#ff6b9d", s=200, marker="P", zorder=8) # desenha uma cruz rosa e a legenda próximo do ponto

    # Sabor Express
    xse, yse = G.nodes[sabor_no]["pos"] # pega a posição da empresa
    ax.scatter(xse, yse, c="#27ae60", s=300, marker="*", zorder=9) # desenha uma estrela e a legenda próximo do ponto

    # Legenda
    legenda = [mpatches.Patch(color="#27ae60",  label="Sabor Express"),
               mpatches.Patch(color="#2d3561",  label="Rua mão dupla"),
               mpatches.Patch(color="#e67e22",  label="Mão única ↗"),
               mpatches.Patch(color="#f1c40f",  label="Zona lenta 30 km/h"),
               mpatches.Patch(color="#8e44ad",  label="Proibido carga pesada"),
               mpatches.Patch(color="#e67e22",  label="Bloqueio Obras"),
               mpatches.Patch(color="#ff1744",  label="Bloqueio Acidente"),
               mpatches.Patch(color="#3498db",  label="Escola"),
               mpatches.Patch(color="#ff6b9d",  label="Hospital")]
    
    for eid in sorted(grupos.keys()): # para cada entregador na ordem criada dos grupos
        cor   = CORES_ENTREGADORES[eid % len(CORES_ENTREGADORES)] # pega a cor do entregador
        n_ent = len(grupos[eid]) # pega o número de entregas do entregador
        legenda.append(mpatches.Patch(color=cor, label=f"Entregador {eid+1}: {n_ent} entregas")) # adiciona na legenda entregadores com sua cor e quantidade de entregas

    ax.legend(handles=legenda, loc="upper left", fontsize=8.5, facecolor="white", framealpha=0.95, bbox_to_anchor=(1.01, 1), borderaxespad=0) # desenha a legenda ao lado direito do mapa
    ax.set_title(f"Rota A*", fontsize=13, fontweight="bold", pad=15) # insere o título no mapa
    ax.set_xlabel("x", fontsize=11) # plota os nomes dos eixos
    ax.set_ylabel("y", fontsize=11)
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True) # plota os marcadores nos eixos
    plt.subplots_adjust(right=0.75) # ajusta espaçamento
    plt.show() # abre e exibe o mapa

#  EXECUÇÃO
G, grade_ids, saborexpress_no, info_restricoes = carregar_cidade() # carrega a cidade
bloqueios = aplicar_bloqueios(G, saborexpress_no) # gera os bloqueios
entregas = gerar_entregas(G, saborexpress_no) # gera os pontos de entrega
grupos = agrupar_entregas(G, entregas) # agrupa as entregas por entregador

rotas_por_entregador = {}
sequencias_por_entregador = {}

print(f"\n  Calculando rotas com A*...")
for eid, nos_entrega in grupos.items(): # para cada entrega de cada entregador
        sequencia = montar_sequencia_entregador(G, saborexpress_no, nos_entrega) # monta a sequencia das entregas 
        rota, custo, segmento = calcular_rota_astar(G, sequencia)
        rotas_por_entregador[eid] = rota
        sequencias_por_entregador[eid] = sequencia

visualizar_rota(G, saborexpress_no, info_restricoes, bloqueios, grupos, rotas_por_entregador, sequencias_por_entregador)
