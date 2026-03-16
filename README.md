# Rota Inteligente: Otimização de Entregas com Algoritmos de IA

## Problema
A empresa " Sabor Express" tem enfrentado grandes desafios para gerenciar suas entregas durante horários de pico, especialmente em períodos de alta demanda, como hora do almoço e jantar.
Os entregadores demoram mais que o previsto, percorrendo rotas ineficientes, o que gera atrasos, aumento no custo de combustível e, consequentemente, insatisfação dos clientes.
O problema a ser resolvido consiste em implementar um algoritmo que encontre, de forma eficiente, o menor caminho entre múltiplos pontos de entrega, considerando as restrições urbanas.

Esse sistema faz uma simulação de logística urbana com geração de mapa de cidade, restrições de trânsito e cálculo de rotas otimizadas com múltiplos entregadores.

## Visão Geral
O projeto é composto por dois módulos principais:
|  Arquivo             | Descrição                                                             |
|----------------------|-----------------------------------------------------------------------|
| "cidade_grafo.py"    | Gera e salva o mapa da cidade como um grafo dirigido                  |
| "rota_inteligente.py"| Carrega o mapa, gera entregas aleatórias e calcula as rotas otimizadas|

## Estrutura do Projeto
├── cidade_grafo.py # Módulo 1: geração do mapa
├── rota_inteligente.py # Módulo 2: roteamento inteligente
├── mapacidade.pkl # Arquivo gerado após executar cidade_grafo.py
└── README.md

## Bibliotecas necessárias via pip
'''
bash
pip install numpy matplotlib networkx scikit-learn
'''
| Biblioteca    | Uso                               |
|---------------|-----------------------------------|
| "numpy"       | Cálculos numéricos e coordenadas  |
| "matplotlib"  | Visualização do mapa e rotas      |
| "networkx"    | Criação e manipulação do grafo    |
| "scikit-learn"| Agrupamento de entregas (K-Means) |
| "pickle"      | Serialização e leitura do grafo   |
| "heapq"       | Fila de prioridade do algoritmo A*|

## Módulo 1
Responsável por criar o mapa da cidade e salvá-lo em arquivo. **Execute apenas uma vez** (ou quando quiser alterar as configurações da cidade).

### Como executar
'''
bash
python cidade_grafo.py
'''

### O que ele faz
- Gera uma malha urbana **30×30** com coordenadas variadas para simular ruas reais
- Cria um **grafo dirigido** ("DiGraph") com nós (cruzamentos) e arestas (ruas)
- Define **20% das ruas como mão única** aleatoriamente, com seed fixo
- Posiciona pontos especiais fixos no mapa:
  - **Sabor Express** — ponto de partida de todas as entregas
  - **2 Escolas** — geram zona de velocidade reduzida (30 km/h) ao redor
  - **1 Hospital** — gera zona de velocidade reduzida (30 km/h) ao redor
- Marca **20% dos nós centrais** como proibidos para carga pesada
- Salva o grafo em "mapacidade.pkl"
- Exibe o mapa completo com legenda

### Configurações (constantes editáveis)
| Constante         | Valor padrão          | Descrição                            |
|-------------------|-----------------------|--------------------------------------|
| "SEED_CIDADE"     | "42"                  | Semente para reprodução da cidade    |
| "GRADE"           | "30"                  | Tamanho da malha (30×30 nós)         |
| "ESPACAMENTO_BASE"| "10"                  | Distância base entre cruzamentos     |
| "VARIACAO"        | "0.25"                | Variação de ±25% no espaçamento      |
| "SABOR_EXPRESS"   | "(120, 85)"           | Coordenada da empresa                |
| "PERC_MAO_UNICA"  | "0.20"                | Proporção de ruas mão única          |
| "PERC_NO_CARGA"   | "0.20"                | Proporção de nós proibidos para carga|
| "ESCOLAS_POS"     | "[(60,60), (200,200)]"| Posições das escolas                 |
| "HOSPITAL_POS"    | "(120, 160)"          | Posição do hospital                  |

### Legenda do mapa gerado
| Cor      | Elemento              |
|----------|-----------------------|
| Verde    | Sabor Express         |
| Cinza    | Rua normal (mão dupla)|
| Laranja  | Rua mão única         |
| Amarelo  | Zona lenta 30 km/h    |
| Roxo     | Proibido carga pesada |
| Azul     | Escola                |
| Vermelho | Hospital              |

## Módulo 2
Responsável por simular uma rodada de entregas: gera bloqueios aleatórios, gera os pedidos, agrupa por entregador e calcula as rotas inteligentes.

### Como executar
'''
bash
python rota_inteligente.py
'''
> ⚠️ O arquivo "mapacidade.pkl" precisa existir antes de executar este módulo. Execute "cidade_graf.py" primeiro.

### O que ele faz
Cada execução gera uma rodada diferente com:
1. **Bloqueios aleatórios** — 3 ruas por obras e 2 por acidente são bloqueadas temporariamente
2. **Geração de entregas** — entre 10 e 50 pontos de entrega sorteados aleatoriamente
3. **Agrupamento por entregador** — K-Means divide as entregas por proximidade entre até 5 entregadores (máximo 10 entregas cada)
4. **Sequência de entrega** — algoritmo *Nearest Neighbor* ordena as entregas de cada entregador pela menor distância consecutiva
5. **Cálculo de rota com A*** — encontra o caminho de menor custo entre cada par de pontos, respeitando bloqueios, mão única e zonas lentas
6. **Visualização** — exibe o mapa com todas as rotas, pontos de entrega numerados e bloqueios

### Algoritmos utilizados

#### A* (A-Star)
Calcula o **caminho de menor custo** entre dois nós do grafo. Usa:
- **g(n)**: custo acumulado real até o nó atual
- **h(n)**: heurística admissível — distância euclidiana até o destino
- **f(n) = g(n) + h(n)**: prioridade na fila

Penalidades aplicadas no custo das arestas:

| Situação             | Comportamento                      |
|----------------------|------------------------------------|
| Rua bloqueada        | Custo infinito (não utilizada)     |
| Zona lenta (30 km/h) | Peso × 1,8 (penalidade)            |
| Rua normal           | Peso direto (distância euclidiana) |

#### K-Means
Agrupa os pontos de entrega por **proximidade geográfica**, minimizando a distância percorrida por entregador. Após o agrupamento, os nós de cada grupo são ordenados pela distância ao centróide.

#### Nearest Neighbor
Ordena a sequência de entregas de cada entregador escolhendo sempre o ponto mais próximo ainda não visitado, partindo da Sabor Express.

### Configurações (constantes editáveis)
| Constante           | Valor padrão | Descrição                        |
|---------------------|--------------|----------------------------------|
| "MAX_ENTREGADORES"  | "5"          | Número máximo de entregadores    |
| "MAX_ENTREGAS_POR"  | "10"         | Máximo de entregas por entregador|
| "MIN_SORT_ENTREGAS" | "10"         | Mínimo de entregas por rodada    |
| "MAX_SORT_ENTREGAS" | "50"         | Máximo de entregas por rodada    |

### Legenda do mapa de rotas
| Cor                                  | Elemento                            |
|--------------------------------------|-------------------------------------|
| Verde (estrela)                      | Sabor Express                       |
| Cor do entregador (linha)            | Rota calculada pelo A*              |
| Cor do entregador (círculo numerado) | Ponto de entrega com ordem de visita|
| Laranja (X)                          | Bloqueio por obras                  |
| Vermelho (X)                         | Bloqueio por acidente               |
| Azul (quadrado)                      | Escola                              |
| Rosa (cruz)                          | Hospital                            |
| Roxo (quadrado)                      | Proibido carga pesada               |

## Fluxo de Execução
'''
1. python cidade_grafo.py
        │
        ▼
   Gera grafo 30×30
   Define restrições fixas
   Salva em mapacidade.pkl
   Exibe mapa da cidade
        │
        ▼
2. python rota_inteligente.py   ← execute quantas vezes quiser
        │
        ▼
   Carrega mapacidade.pkl
   Aplica bloqueios aleatórios
   Sorteia entregas
   Agrupa por K-Means
   Ordena por Nearest Neighbor
   Calcula rotas com A*
   Exibe mapa de rotas
'''

## Observações
- O mapa da cidade é **determinístico**: a mesma "SEED_CIDADE" sempre gera a mesma cidade.
- As rotas são **não-determinísticas**: cada execução de "rota_inteligente.py" gera entregas e bloqueios diferentes.
- Arestas de mão única respeitam a **direção** no grafo dirigido — o A* não passa por elas no sentido contrário.
- O algoritmo garante retorno à Sabor Express ao final de cada rota.

# Sugestões e limitações
- O algoritmo A* não encontra a melhor solução, mas a mais aceitável dentro das condições complexas do problema.
- O algoritmo A* equilibra o já conhecido (percorrido) com o desconhecido (heurística) encontrando uma solução aceitável de forma rápida para um problema muito difícil/complexo.
- O traballho pode ser evoluído para um mapa real com coordenadas geográficas além de permitir que o usuário possa inserir as coordenadas dos locais de entrega, gerando uma rota real para uma cidade real.
- A principal mudança é a fonte dos dados — em vez de gerar o grafo artificialmente, você usaria dados reais de ruas.
- Usaria a biblioteca OSMnx, que baixa dados do OpenStreetMap e já entrega um DiGraph do NetworkX
- O grafo já vem com:
    Nós com atributo x, y (coordenadas geográficas)
    Arestas com length (distância real em metros)
    Sentido das ruas (mão única já mapeado)
- No mapa real, o peso ideal para o A* é o tempo de viagem, não só a distância
- Para plotar as rotas sobre o mapa real em vez da grade cinza, o OSMnx tem função nativa
- O núcleo do sistema — A*, K-Means, Nearest Neighbor, agrupamento por entregador — não precisaria mudar nada.