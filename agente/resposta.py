"""Monta a resposta sem IA: o roteador escolhe os blocos de fatos, e o texto sai sempre no mesmo formato.

Formato (nota de regras, "O caso de uso principal"): aviso, uma vez só (D2, D3) → 3 linhas para o celular, a 1ª é a
recusa quando há pedido de dica (D7) → o que cada pedido específico não recebe → os blocos de fatos (candidatos, economia,
o que o mercado espera, o que aconteceu antes, datas marcadas, pesquisas registradas, como o mercado funciona, taxa-base)
→ limitações → fontes numeradas. Nada repete o aviso: em 22/10/2026 uma recusa dizia "não" 9 vezes.
É também a resposta de segurança do modo com IA: se a IA escrever algo que o filtro barra, a pessoa recebe esta.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

from coletor.config import FUSO

from . import fatos as F
from . import textos as T
from .filtro import Violacao, checar
from .roteador import CONTRATO, MERCADOS, PRECO_EM_DOLAR, Pedido, analisar, normalizar

DERIVATIVOS = ('mini_indice', 'mini_dolar', 'juros')
# O mercado da pergunta e a série que mede o caminho dele.
MEDIDO = {'mini_indice': 'ibovespa', 'mini_dolar': 'dolar', 'petroleo': 'brent'}


@dataclass
class Resposta:
    pergunta: str
    pedido: Pedido
    curta: list[str]
    blocos: list[F.Bloco]
    abertura: list[str]
    texto: str = ''
    texto_curto: str = ''  # o que o celular mostra primeiro: aviso, 3 linhas, riscos, fecho e fontes
    fatos: str = ''  # tudo o que a resposta pode citar: os blocos e os textos fixos
    modo: str = 'sem IA'
    violacoes: list[Violacao] = field(default_factory=list)


def _medidos_cambio(p: Pedido) -> list[str]:
    """Os mercados para os blocos medidos (eleições, Copom): em pergunta de câmbio, o dólar vem primeiro e o euro sai
    (ele tem bloco próprio)."""
    if not p.cambio:
        return p.mercados
    return ['dolar'] + [m for m in p.mercados if m not in ('dolar', 'euro')]


def escolher_blocos(p: Pedido, hoje: str) -> list[F.Bloco]:
    blocos: list[F.Bloco] = []
    pede_dinheiro = 'chance_dinheiro' in p.proibidos
    medidos_cambio = _medidos_cambio(p)
    if p.eleicao:
        blocos += [F.candidatos(), F.economia(), F.eleicoes(medidos_cambio), F.pesquisas()]
    if 'copom' in p.temas:
        if not p.eleicao:
            blocos.append(F.economia())
        blocos.append(F.copom(medidos_cambio))
    # Em pergunta de petróleo, guerra e choque externo vêm pelo bloco do petróleo, que mede também o Brent, quando ele cobre
    # o assunto: tarifa, sanção e guerra comercial não são guerra do petróleo, e ficam na linha do tempo.
    t = normalizar(p.pergunta)
    temas_petroleo = F.tema_petroleo(t) if 'petroleo' in p.mercados else ()
    coberto = {'geopolitico': 'guerra' in temas_petroleo and not re.search(TARIFA_DITA, t),
               'choque_externo': 'choque' in temas_petroleo}
    tipos = [x for x in F.TIPOS if x in p.temas and not coberto.get(x)]
    for tipo in tipos:
        blocos.append(F.eventos(tipo))
    tem_economia = lambda: any(b and b.titulo.startswith('A economia hoje') for b in blocos)  # noqa: E731
    if 'economia' in p.temas and not tem_economia():
        blocos.insert(0, F.economia())
    # Pedido de direção sobre um mercado sem evento no repertório ("é topo?", "qual o viés?"): ao menos o nível de hoje.
    if p.mercados and T.PEDEM_RECUSA & set(p.proibidos) and not tem_economia():
        blocos.insert(0, F.economia())
    # Mercado sem evento no repertório ("devo comprar dólar?", "como está o Ibovespa?"): o caminho que ele já fez, o que o
    # mercado espera (Focus, atribuído) e as datas marcadas que já mexeram com ele.
    # A linha do tempo que fica numa pergunta de petróleo não tira o caminho do Brent nem os dois lados.
    tem_evento = p.eleicao or 'copom' in p.temas or any(x not in coberto or 'petroleo' not in p.mercados for x in tipos)
    medidos = [m for m in dict.fromkeys(MEDIDO.get(m, m) for m in p.mercados) if m in F.HISTORICO]
    # "ETF de bitcoin na B3", "bitcoin na bolsa": a B3 é o lugar da cripto, não o Ibovespa. Sem caminho nem dois lados do
    # índice. "Bitcoin ou bolsa?", "bitcoin ou WIN?" citam o índice: os dois mercados.
    b3_so_lugar = ('cripto' in p.mercados and 'mini_indice' not in p.mercados
                   and not re.search(IBOV_DITO, re.sub(LUGAR_DITO, ' ', t)))
    if b3_so_lugar:
        medidos = [m for m in medidos if m != 'ibovespa']
    # "10 mil dólares em bitcoin": o dólar é a unidade do valor, não o mercado da pergunta (como no petróleo, no roteador).
    # O mini-dólar (WDO) mede o dólar de verdade.
    if ('cripto' in p.mercados and 'mini_dolar' not in p.mercados
            and not re.search(MERCADOS['dolar'], re.sub(PRECO_EM_DOLAR, ' ', t))):
        medidos = [m for m in medidos if m != 'dolar']
    if not tem_evento and medidos:
        blocos += [F.historico(m) for m in medidos]
        # Quem pede o que fazer ou para onde vai recebe os dois lados do que já aconteceu, não uma recomendação. Em contrato
        # (WIN, WDO) não: o lado que importa é a taxa-base da FGV, que precisa caber nas 3 linhas.
        if {'dica', 'direcao', 'momento'} & set(p.proibidos) and not {'mini_indice', 'mini_dolar'} & set(p.mercados):
            blocos += [F.dois_lados(m) for m in medidos]  # de cada mercado citado, não só do primeiro
        # O Focus não pergunta pelo petróleo. Sem o Brent, a expectativa vai para o outro mercado medido; só com o Brent e
        # pergunta de economia (inflação, IPCA, PIB), vai a do tema.
        alvo = next((m for m in medidos if m != 'brent'), '' if 'economia' in p.temas else None)
        blocos += [F.expectativas(alvo) if alvo is not None else None, F.calendario(medidos[0], hoje)]
    elif 'economia' in p.temas or 'copom' in p.temas:
        blocos.append(F.expectativas(medidos[0] if medidos else ''))
    if 'memecoin' in p.mercados:
        blocos.append(F.memecoins())
    if 'previsao' in p.mercados:
        blocos.append(F.previsao())
    if 'binaria' in p.proibidos:
        blocos.append(F.binaria())
    if p.conta:
        blocos.append(F.conta(p.pontos, p.contratos, 'mini_indice' if 'mini_indice' in p.mercados else 'mini_dolar'))
    eventos_petroleo = False  # o estudo dos eventos de petróleo também mede o dólar, não o euro
    for m in p.mercados:
        if m == 'ibovespa' and ('mini_indice' in p.mercados or b3_so_lugar):
            continue  # contrato (WIN) ou cripto na B3: a regra de IR das ações à vista não vale
        blocos.append(F.mercado(m))
        if m == 'petroleo':
            # Quem cita só a ação ("vale a pena PETR4?", "PETR4 ou PRIO3?") não recebe a história de um emissor (Res. CVM
            # 20): os eventos entram quando a pergunta cita o fato ou o petróleo. Do barril à bomba, quando ela fala de
            # combustível, ou do petróleo sem tema.
            # Com pedido de dica, direção, momento ou ranking que cita a ação ("compro PETR4 antes do dividendo
            # extraordinário?"), ou com escolha entre ativos ("petróleo ou dólar, qual é melhor?"), os eventos da Petrobras
            # não entram nem com o fato citado: ficam os do petróleo, quando a pergunta cita o petróleo (Mapa legal, seção
            # 8, item 10).
            temas_ev = temas_petroleo
            if T.PEDEM_RECUSA & set(p.proibidos) and (re.search(ACAO_DITA, t) or {'ranking', 'comparar'} & set(p.proibidos)):
                sem_emissor = lambda ts: tuple(x for x in ts if x != 'petrobras')  # noqa: E731
                temas_ev = sem_emissor(temas_petroleo) or (sem_emissor(F._petroleo()['temas'])
                                                           if re.search(PETROLEO_DITO, t) or not re.search(ACAO_DITA, t)
                                                           else ())
            so_acao = not temas_ev and re.search(ACAO_DITA, t) and not re.search(PETROLEO_DITO, t)
            if not so_acao:
                blocos.append(F.petroleo_eventos(temas_ev))
                eventos_petroleo = True
            if re.search(COMBUSTIVEL_DITO, t) or not temas_petroleo and not so_acao:
                blocos.append(F.barril_bomba())
        if m == 'cripto':
            # Regras, imposto, riscos e a linha do tempo. Tema citado (halving, FTX, ETF...): a linha do tempo antes das
            # regras, com a definição primeiro se a pessoa perguntou "o que é". Pergunta de imposto: o imposto primeiro.
            t = normalizar(p.pergunta)
            tema = F.tema_cripto(t)
            # Quem escolhe ou avalia uma corretora pelo nome não recebe a história de uma delas no topo (N7): a linha do
            # tempo inteira vai para o fim, como em qualquer pergunta de cripto sem tema.
            if tema == 'binance' and 'plataforma' in p.proibidos:
                tema = ''
            # Pergunta de imposto do ETF ou do futuro: o resumo diz que a isenção de R$ 35 mil não vale para eles; de
            # declaração: quem declara e como. O que o celular mostra primeiro não pode omitir isso (CDC, art. 37, §3º).
            imposto_dito = bool(re.search(IMPOSTO_DITO, t))
            variante = ('etf' if imposto_dito and (tema == 'etf' or re.search(FUTURO_CRIPTO, t))
                        else 'declaracao' if re.search(DECLARACAO_DITA, t) else '')
            imposto, riscos = F.cripto_imposto(variante), F.cripto_riscos()
            if imposto_dito:
                blocos[-1:-1] = [imposto]
                blocos.append(riscos)
            else:
                blocos += [imposto, riscos]
            if tema:
                # em pergunta de imposto, a linha do tempo vem depois do imposto; a definição só vira a 1ª linha quando o
                # "o que é" é do próprio termo ("o que é a lei das stablecoins nos EUA?" quer a lei, não a stablecoin)
                antes = (F.TITULO_CRIPTO,) if imposto_dito else (F.TITULO_CRIPTO, F.TITULO_CRIPTO_IMPOSTO)
                i = next(i for i, b in enumerate(blocos) if b and b.titulo in antes)
                conceito = 'conceito' in p.temas and bool(re.search(CONCEITO_CRIPTO, t))
                blocos.insert(i, F.cripto_marcos(tema, conceito=conceito))
            else:
                blocos.append(F.cripto_marcos())
    if pede_dinheiro or set(DERIVATIVOS[:2]) & set(p.mercados):
        blocos.append(F.fgv())
    # O estudo do Copom, da linha do tempo e dos eventos de petróleo mede o dólar, não o euro: dizer isso, em vez de
    # responder só com o dólar.
    if 'euro' in p.mercados and ('copom' in p.temas or any(t in p.temas for t in F.TIPOS) or eventos_petroleo):
        blocos.append(F.euro_sem_estudo())
    blocos = [b for b in blocos if b]
    if p.cambio:
        blocos = _cambio_primeiro(p, blocos)
    elif 'cripto' in p.mercados:  # em pergunta de câmbio ("exchange my euros"), o câmbio continua na frente
        blocos = _cripto_primeiro(blocos)
    # A linha do pedido promete a taxa-base da FGV "logo abaixo": ela vai em 2º, depois de qualquer reordenamento.
    if pede_dinheiro:
        fgv = [b for b in blocos if b.titulo == F.TITULO_FGV]
        if fgv:
            blocos = [b for b in blocos if b.titulo != F.TITULO_FGV]
            blocos.insert(min(1, len(blocos)), fgv[0])
    if not blocos:
        blocos.append(F.economia())
    return blocos


CRIPTO_TITULOS = (F.TITULO_MARCOS, F.TITULO_CRIPTO, F.TITULO_CRIPTO_IMPOSTO, F.TITULO_CRIPTO_RISCOS)
# A pessoa falou do índice mesmo, e não só da B3 como lugar. "Bolsa de cripto", "índice de medo" e "stock-to-flow" são
# da cripto.
IBOV_DITO = (r'\bibov\w*|\bbovespa\b|\bacoes\b|\bacao\b|\bbova11\b|\bbolsa\b(?! de (cripto|bitcoin))'
             r'|\bstocks?\b(?![- ]to[- ]flow)|\bindices?\b(?! de (medo|dominancia))')
# "bitcoin na bolsa", "ETF de bitcoin na bolsa": a bolsa como lugar da cripto, igual à B3. Também a escolha do lugar
# ("corretora ou bolsa, onde compro bitcoin?", "bolsa ou exchange?") e o "fundo de índice" (o ETF), que não são o Ibovespa.
LUGAR_DITO = (r'\b(cripto\w*|bitcoins?|btc|ethereum|eth|hash11|etfs?|futuros?)( de \w+)? (na|pela|da|via) (bolsa|b3)\b'
              r'|\b(corretora|exchange|direto) (ou|vs|x|versus) (a |na |pela )?bolsa\b'
              r'|\bbolsa (ou|vs|x|versus) (a |o |na |no |pela |pelo )?(corretora|exchange|direto)\b'
              r'|\b(fundos?|etfs?) de indices?\b')
TARIFA_DITA = (r'\btarifa\w*|\bsobretaxa\w*|\btaxac\w* (d[aoe]s? )?(trump|eua|estados unidos|americana)\b|\bsanc(ao|oes)\b'
               r'|\bguerra comercial\b')
ACAO_DITA = r'\b(petrobras|petr[34]|prio3?|petroleiras?|acao|acoes)\b'
PETROLEO_DITO = r'\b(petroleo|brent|wti|barril|opep|opec|ormuz|combustive(l|is)|gasolina|diesel)\b'
COMBUSTIVEL_DITO = (r'\b(gasolina|diesel|etanol|combustive(l|is)|bomba|posto|litro|reajust\w*|ipca|inflacao|defasa\w*'
                    r'|paridade|politica de preco\w*)\b')
# "declarar" e "declaração" (não "declarou", nem "declarar guerra"); o "IR" dito com verbo ou preposição ("bitcoin paga IR?",
# "o IR da cripto"), sem "de ir" ("é hora de ir pro bitcoin?").
DECLARACAO_DITA = r'\bdeclar(ar|o|a|as|amos|ei|ando|ado|ados|acao|acoes)\b(?! guerra\b)'
IMPOSTO_DITO = (r'\bimpost\w*|' + DECLARACAO_DITA + r'|\birpf?\b|\bdarf\b|\bleao\b|\btribut\w*|\bisen\w*'
                r'|\b(paga|pagar|pago|pagam|pagou|pagando|cobra|cobram|cobrar|incide|tem|o|do|no) ir\b'
                r'|\bir (da|do|sobre|em|no|na) (cripto\w*|bitcoins?|btc|ether|eth)\b')
FUTURO_CRIPTO = r'\bfuturos? (de|do) (bitcoins?|btc|cripto\w*|ether|ethereum|eth)\b'
# O "o que é" do próprio termo do tema ("o que é halving?", "me explica o halving", "halving, o que é?").
TERMO_CRIPTO = r'(halvings?|stablecoins?|usdt|usdc|tether|etfs?|hash11|ftx|fundos? de indice)'
CONCEITO_CRIPTO = (rf'\bo que (e|sao|significa|foi|quer dizer) (o |a |os |as |um |uma )?{TERMO_CRIPTO}\b'
                   rf'|\bme explica\w* (o |a |os |as )?{TERMO_CRIPTO}\b|\b{TERMO_CRIPTO}\b\W+o que (e|significa)\b'
                   rf'|\bcomo funciona (o |a |os |as )?{TERMO_CRIPTO}\b')
# A pergunta fala da defasagem do preço da Petrobras, que o repertório não calcula: dizer isso no topo (D8).
DEFASAGEM_DITA = r'\bdefasa\w*|\bparidade\b|\babaixo do preco internacional\b'
# Pergunta de preço ou de movimento de cripto: o repertório não tem a cotação.
# Também o gerúndio, o plural, os sinônimos e o internetês ("tá caindo?", "despencou?", "as criptos caíram?", "qnt tá?").
PRECO_CRIPTO = (r'\b((quanto|qnt|qto) (ta|esta|vale|custa)|preco|cotacao|caiu|cairam|subiu|subiram|cai|caem|sobe|sobem'
                r'|caindo|subindo|em (alta|queda)|despenc\w*|desab\w*|derret\w*|dispar\w*|reagiu|valoriz\w*|desvaloriz\w*)\b'
                r'|\bo que (aconteceu|houve) com (o |os |a |as )?(bitcoins?|btc|cripto\w*|ether(eum)?|eth|solana)\b')


def _cripto_primeiro(blocos: list[F.Bloco]) -> list[F.Bloco]:
    """Pergunta que cita cripto: os blocos de cripto na frente ("ETF de bitcoin na B3" fala de cripto, não do nível do
    Ibovespa), na ordem em que já estavam. A taxa-base da FGV, quando há ("dá pra ficar rico?"), logo depois do 1º."""
    eh = lambda b: b.titulo in CRIPTO_TITULOS  # noqa: E731
    fgv = [b for b in blocos if b.titulo == F.TITULO_FGV]
    cripto = [b for b in blocos if eh(b)]
    return cripto[:1] + fgv + cripto[1:] + [b for b in blocos if not eh(b) and b.titulo != F.TITULO_FGV]


def _cambio_primeiro(p: Pedido, blocos: list[F.Bloco]) -> list[F.Bloco]:
    """Pergunta de câmbio: na frente, a conta com os números da pessoa; com eleição, o euro nos turnos e o que o mercado
    espera para o dólar; sem eleição, o caminho do euro e o que o mercado espera. O resto segue na ordem de antes, sem a
    expectativa de outro mercado (a da Selic, numa pergunta de euro e bolsa)."""
    euro = 'euro' in p.mercados
    expectativa = F.expectativas('euro' if euro else 'dolar')
    frente: list[F.Bloco] = []
    if p.conta_cambio:
        frente.append(F.conta_cambio(p.valor_moeda, p.moeda, p.gasto_mensal, p.gasto_moeda))
    if euro and p.eleicao:
        frente += [F.euro_turnos(), expectativa, F.historico('euro')]
    elif euro:
        frente += [F.historico('euro'), expectativa]
    else:
        frente.append(expectativa)
    vistos = {b.titulo for b in frente}
    resto = [b for b in blocos if b.titulo not in vistos and not b.titulo.startswith(F.TITULO_EXPECTATIVAS)]
    return frente + resto


def _abertura(p: Pedido, achou_repertorio: bool) -> list[str]:
    linhas = []
    recusa = bool(T.PEDEM_RECUSA & set(p.proibidos))
    if recusa:
        linhas.append(T.RECUSA)
    for codigo in T.POR_PEDIDO:
        if codigo in p.proibidos and not (recusa and codigo == 'direcao'):  # a RECUSA já diz que não dá direção
            linhas.append(T.POR_PEDIDO[codigo])
    if 'memecoin' in p.mercados and T.PEDEM_RECUSA & set(p.proibidos) and 'plataforma' not in p.proibidos:
        linhas.append(T.POR_PEDIDO['plataforma'])
    if 'cripto' in p.mercados and re.search(PRECO_CRIPTO, normalizar(p.pergunta)):
        linhas.append(T.SEM_PRECO_CRIPTO)
    if 'petroleo' in p.mercados and re.search(DEFASAGEM_DITA, normalizar(p.pergunta)):
        linhas.append(T.SEM_DEFASAGEM)
    if p.voto_informado:
        linhas.append(T.VOTO_INFORMADO)
    if not achou_repertorio:
        linhas.append(T.SEM_REPERTORIO)
    return linhas


def _curta(p: Pedido, blocos: list[F.Bloco], abertura: list[str]) -> list[str]:
    """Até 3 linhas do que dá para saber. A recusa e a linha de cada pedido ficam no topo, antes delas."""
    linhas = []
    if T.SEM_REPERTORIO in abertura:
        linhas.append('Não achei caso parecido no repertório; ele mostra o que já aconteceu, e abaixo está o que cobre.')
    resumos = [b.resumo for b in blocos if b.resumo]
    # Por último: as datas marcadas e o último dado da economia. Primeiro o que aconteceu e o que o mercado espera.
    resumos.sort(key=lambda r: 2 if r.startswith(F.RESUMO_HOJE) else 1 if r.startswith(F.CALENDARIO['resumo_inicio']) else 0)
    linhas += resumos
    return linhas[:3]


def _contrato_de_juros(pergunta: str) -> bool:
    """'juros' é o mercado de renda fixa, Selic e DI futuro; só o DI futuro é derivativo (D4)."""
    return bool(re.search(CONTRATO + r'|\bfuturos?\b', normalizar(pergunta)))


def _avisos(r: Resposta) -> list[str]:
    avisos = []
    derivativo = (set(DERIVATIVOS[:2]) & set(r.pedido.mercados) or ('juros' in r.pedido.mercados and _contrato_de_juros(r.pergunta))
                  or any(b.titulo == F.TITULO_CRIPTO_IMPOSTO for b in r.blocos))  # ele cita o futuro de bitcoin
    if derivativo or any(b.titulo.startswith('A taxa-base de quem faz day') for b in r.blocos):
        avisos.append(T.RISCO_DERIVATIVO_CRIPTO if 'cripto' in r.pedido.mercados else T.RISCO_DERIVATIVO)
    if {'cripto', 'memecoin'} & set(r.pedido.mercados) and not any(b.titulo == F.TITULO_CRIPTO for b in r.blocos):
        avisos.append(T.RISCO_CRIPTO)  # o bloco da cripto já traz o D5: não repete
    return avisos


def renderizar(r: Resposta) -> tuple[str, str]:
    """O texto inteiro e a versão curta, com a mesma numeração de fontes."""
    fontes: list[F.Fonte] = []

    def ref(f: F.Fonte) -> str:
        if f not in fontes:
            fontes.append(f)
        return f'[{fontes.index(f) + 1}]'

    # Topo, igual nas duas versões: o aviso, a recusa e a linha de cada pedido (capital, stop, ranking...), uma vez só.
    topo = [T.AVISO]
    for x in r.abertura:
        if x != T.SEM_REPERTORIO:
            topo += ['', x]
    if r.curta:
        topo += ['', '**Em 3 linhas**' if len(r.curta) == 3 else '**Em resumo**']
        topo += [f'{i}. {x}' for i, x in enumerate(r.curta, 1)]
    partes = list(topo)
    if T.SEM_REPERTORIO in r.abertura:
        partes += ['', T.SEM_REPERTORIO]
    limites = []
    for b in r.blocos:
        partes += ['', f'**{b.titulo}**']
        for ln in b.linhas:
            refs = ''.join(ref(f) for f in ln.fontes)
            partes.append(f'- {ln.texto}' + (f' {refs}' if refs else ''))
        limites += [x for x in b.limites if x not in limites]
    avisos = _avisos(r)
    if avisos:
        partes += ['', '**Riscos deste mercado**'] + [f'- {a}' for a in avisos]
    if limites:
        partes += ['', '**Limitações**'] + [f'- {x}' for x in limites]
    partes += ['', '**Fontes**']
    lista = [f'[{i}] {f.nome}' + (f': {f.url}' if f.url else '') for i, f in enumerate(fontes, 1)]
    partes += lista
    # Versão curta: as fontes das 3 linhas (até 4), com o mesmo número do texto inteiro. Uma de cada linha por vez, na
    # ordem das linhas, para nenhuma ficar sem fonte; dentro de cada uma, primeiro as séries oficiais e as pesquisas
    # (o arquivo do TSE é grande demais para o celular).
    def oficial(f: F.Fonte) -> bool:
        return f.nome.startswith(('Banco Central', 'Ipeadata', 'Tesouro', 'Pesquisa', 'Chague'))

    por_linha = []
    for resumo in r.curta:
        b = next((b for b in r.blocos if b.resumo and b.resumo == resumo), None)
        if b is None:
            continue
        fs: list[F.Fonte] = []
        for ln in b.linhas:
            for f in ln.fontes:
                if f.url and f not in fs:
                    fs.append(f)
        fs.sort(key=lambda f: not oficial(f))
        por_linha.append(fs)
    das_linhas: list[F.Fonte] = []
    for i in range(max((len(fs) for fs in por_linha), default=0)):
        for fs in por_linha:
            if i < len(fs) and fs[i] not in das_linhas:
                das_linhas.append(fs[i])
    curto = list(topo)
    # A versão curta só leva as 3 linhas: se elas falam de cripto e nenhuma diz que não é valor mobiliário (D5), o aviso
    # de cripto entra mesmo que o bloco dele esteja no texto inteiro.
    if (T.RISCO_CRIPTO not in avisos and {'cripto', 'memecoin'} & set(r.pedido.mercados)
            and not any('não é valor mobiliário' in x for x in r.curta)):
        avisos = avisos + [T.RISCO_CRIPTO]
    curto += [''] + avisos if avisos else []
    if das_linhas:
        curto += ['', 'Fontes: ' + ' · '.join(f'{f.nome}: {f.url}' for f in das_linhas[:4])]
    return '\n'.join(partes), '\n'.join(curto)


def fatos_texto(r: Resposta) -> str:
    """O que a resposta pode citar: os blocos com as fontes, e os textos fixos (com os números deles)."""
    partes = []
    for b in r.blocos:
        partes.append(f'## {b.titulo}')
        partes += [f'- {ln.texto} (fontes: {"; ".join(f"{f.nome} {f.url}".strip() for f in ln.fontes) or "nenhuma"})' for ln in b.linhas]
        if b.limites:
            partes.append('Limitações: ' + ' '.join(b.limites))
    fixos = [T.AVISO, T.RECUSA, T.FECHO, T.RISCO_DERIVATIVO, T.RISCO_CRIPTO, T.SEM_REPERTORIO, T.NORMAS, T.VOTO_INFORMADO,
             T.SEM_PRECO_CRIPTO, T.RISCO_DERIVATIVO_CRIPTO, T.SEM_DEFASAGEM,
             *T.POR_PEDIDO.values()]
    return '\n'.join(partes + ['## Textos fixos'] + fixos)


SEGURA = ('Não consegui montar esta resposta dentro das regras, e o caso foi registrado para revisão. Pergunte de outro '
          'jeito, por exemplo sobre um evento passado.')


def montar(pergunta: str, pedido: Pedido | None = None, hoje: str | None = None) -> Resposta:
    """A resposta inteira, sempre da base. `pedido` é a leitura já feita (palavras-chave somadas à da IA); `hoje`
    (AAAA-MM-DD, horário de Brasília) decide quais datas marcadas ainda aparecem."""
    p = pedido or analisar(pergunta)
    hoje = hoje or datetime.now(FUSO).date().isoformat()
    tem_tema = bool(p.mercados or p.temas or p.candidatos or p.eleicao or {'binaria', 'chance_dinheiro'} & set(p.proibidos))
    blocos = escolher_blocos(p, hoje)
    abertura = _abertura(p, tem_tema)
    r = Resposta(pergunta, p, _curta(p, blocos, abertura), blocos, abertura)
    r.texto, r.texto_curto = renderizar(r)
    r.fatos = fatos_texto(r)
    r.violacoes = checar(r.texto, r.fatos) + [v for v in checar(r.texto_curto, r.fatos) if v.regra != 'D1' or
                                               'http' not in r.texto]
    if r.violacoes:
        # Defeito de dado ou de modelo de texto: a pessoa recebe só os avisos e a recusa; o resto fica no registro.
        r.texto = r.texto_curto = '\n\n'.join([T.AVISO, SEGURA])
    return r
