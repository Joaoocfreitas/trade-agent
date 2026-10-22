"""Caminhos, identificação do robô e limites de educação com os sites."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / 'dados'
FONTES_DIR = DADOS / 'fontes'
COLETA_DIR = DADOS / 'coleta'
COFRE = Path(os.environ.get('TRADE_COFRE', Path.home() / 'Documents' / 'trade-obsidian' / 'Trade'))
FUSO = ZoneInfo('America/Sao_Paulo')

# O robô se identifica como robô. Nada de se passar por navegador de gente.
ROBO = 'TradeAgentPesquisa'
# O robô diz quem é e onde ver o produto (22/10/2026: o dado passa a alimentar um site com plano pago, então "pesquisa
# pessoal sem fins comerciais" deixou de ser verdade). O nome que o robots.txt lê continua o mesmo.
USER_AGENT = f'Mozilla/5.0 (compatible; {ROBO}/0.2; +https://thoran-rho.vercel.app)'

TIMEOUT_S = 20
INTERVALO_MESMO_DOMINIO_S = 1.5  # contado do FIM do pedido anterior ao mesmo domínio
FEEDS_SIMULTANEOS = 6
PAGINAS_SIMULTANEAS = 3
ITENS_POR_FEED = 30
ARTIGOS_POR_FEED = 3
PALAVRAS_MINIMAS = 120
MAX_REDIRECIONAMENTOS = 5
MAX_BYTES_FEED = 40_000_000  # há feed de podcast com 21 MB de histórico
MAX_TENTATIVAS = 3  # falha passageira (rede, 429, 503) é tentada de novo até aqui

# 'api_gratis' fica de fora: é dado estruturado, vai para o pipeline de dados (fase 2), não para o crawler.
ACESSOS_COLETAVEIS = frozenset({'eu_busco', 'misto'})

# chave da categoria -> (pasta no cofre, subpasta)
CATEGORIAS = {
    'pessoas_br_mercado': ('1 Pessoas', 'Brasil — mercado'),
    'pessoas_br_politica': ('1 Pessoas', 'Brasil — política e colunistas'),
    'pessoas_global': ('1 Pessoas', 'Global'),
    'imprensa_br': ('2 Imprensa', 'Brasil'),
    'imprensa_global': ('2 Imprensa', 'Internacional'),
    'programas': ('3 Programas e podcasts', None),
    'dados': ('4 Dados e ferramentas', None),
    'politica': ('5 Política e eleições', None),
    'mercados_previsao': ('6 Mercados de previsão', None),
    'metodo': ('7 Ciência e regras', None),
}
