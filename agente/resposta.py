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
from .roteador import CONTRATO, Pedido, analisar, normalizar

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
    # Em pergunta de petróleo, guerra e choque externo vêm pelo bloco do petróleo, que mede também o Brent.
    tipos = [t for t in F.TIPOS if t in p.temas and not ('petroleo' in p.mercados and t in ('geopolitico', 'choque_externo'))]
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
    tem_evento = p.eleicao or 'copom' in p.temas or bool(tipos)
    medidos = [m for m in dict.fromkeys(MEDIDO.get(m, m) for m in p.mercados) if m in F.HISTORICO]
    # "ETF de bitcoin na B3": a B3 é o lugar da cripto, não o Ibovespa. Sem caminho nem dois lados do índice.
    b3_so_lugar = 'cripto' in p.mercados and not re.search(IBOV_DITO, normalizar(p.pergunta))
    if b3_so_lugar:
        medidos = [m for m in medidos if m != 'ibovespa']
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
    for m in p.mercados:
        if m == 'ibovespa' and ('mini_indice' in p.mercados or b3_so_lugar):
            continue  # contrato (WIN) ou cripto na B3: a regra de IR das ações à vista não vale
        blocos.append(F.mercado(m))
        if m == 'petroleo':
            blocos += [F.petroleo_eventos(F.tema_petroleo(normalizar(p.pergunta))), F.barril_bomba()]
        if m == 'cripto':
            # Regras, imposto, riscos e a linha do tempo. Tema citado (halving, FTX, ETF...): a linha do tempo antes das
            # regras, com a definição primeiro se a pessoa perguntou "o que é". Pergunta de imposto: o imposto primeiro.
            t = normalizar(p.pergunta)
            tema = F.tema_cripto(t)
            imposto, riscos = F.cripto_imposto(), F.cripto_riscos()
            if re.search(IMPOSTO_DITO, t):
                blocos[-1:-1] = [imposto]
                blocos.append(riscos)
            else:
                blocos += [imposto, riscos]
            if tema:
                i = next(i for i, b in enumerate(blocos) if b and b.titulo in (F.TITULO_CRIPTO, F.TITULO_CRIPTO_IMPOSTO))
                blocos.insert(i, F.cripto_marcos(tema, conceito='conceito' in p.temas))
            else:
                blocos.append(F.cripto_marcos())
    if pede_dinheiro or set(DERIVATIVOS[:2]) & set(p.mercados):
        blocos.append(F.fgv())
    # O estudo do Copom e da linha do tempo mede o dólar, não o euro: dizer isso, em vez de responder só com o dólar.
    if 'euro' in p.mercados and ('copom' in p.temas or any(t in p.temas for t in F.TIPOS)):
        blocos.append(F.euro_sem_estudo())
    blocos = [b for b in blocos if b]
    if p.cambio:
        blocos = _cambio_primeiro(p, blocos)
    elif 'cripto' in p.mercados:  # em pergunta de câmbio ("exchange my euros"), o câmbio continua na frente
        blocos = _cripto_primeiro(blocos)
    if not blocos:
        blocos.append(F.economia())
    return blocos


CRIPTO_TITULOS = (F.TITULO_MARCOS, F.TITULO_CRIPTO, F.TITULO_CRIPTO_IMPOSTO, F.TITULO_CRIPTO_RISCOS)
# A pessoa falou do índice mesmo, e não só da B3 como lugar.
IBOV_DITO = r'\bibov\w*|\bbovespa\b|\bacoes\b|\bacao\b|\bbova11\b'
IMPOSTO_DITO = r'\bimpost\w*|\bdeclar\w*|\birpf?\b|\bdarf\b|\bleao\b|\btribut\w*|\bisen\w*'
# Pergunta de preço ou de movimento de cripto: o repertório não tem a cotação.
PRECO_CRIPTO = (r'\b(quanto (ta|esta|vale|custa)|preco|cotacao|caiu|subiu|cai|sobe|reagiu|valoriz\w*|desvaloriz\w*)\b'
                r'|\bo que aconteceu com o (bitcoin|btc|cripto)')


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
             T.SEM_PRECO_CRIPTO, T.RISCO_DERIVATIVO_CRIPTO,
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
