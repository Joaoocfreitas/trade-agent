"""O registro de todas as conversas (M10): pergunta, resposta mostrada, texto da IA barrado e o porquê.

Sem dado pessoal: o valor em reais e o voto que a pessoa contar saem antes de gravar (N5, N9 e LGPD). Não há nome,
e-mail nem identificador de quem perguntou. O arquivo fica fora do git.
"""
import json
import os
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from coletor.config import FUSO
from .fatos import AGENTE
from .roteador import cambio, normalizar, simples

# TRADE_AGENTE_REGISTRO aponta outro arquivo (testes e ataques não sujam o registro de verdade).
ARQUIVO = Path(os.environ.get('TRADE_AGENTE_REGISTRO') or AGENTE / 'conversas.jsonl')

# Opinião política é dado sensível (LGPD, art. 5º, II): a oração inteira que fala de voto ou de lado sai.
POLITICO = re.compile(
    r'\bvot(o|ei|ar|arei|aria|ando|amos|e|ou|aram|ara)\b|\bmeu voto\b|\bvou de\b|\bfui de\b|\bfiz o l\b|\bfaz o l\b|\bapoi(o|ar|ador\w*)\b|\btorc(o|endo|er)\b'
    r'|\beleitor\w*|\bmeu candidato\b|\bminha candidata\b|\bsou (do|da) (pt|pl|psol|novo|psdb|mdb|pdt|psb)\b'
    r'|\bsou (\w+ )?(de )?(direita|esquerda)\b|\b(petista|bolsonarista|lulista|esquerdista|direitista|bolsominion\w*|antipetista'
    r'|antibolsonarista|conservador\w*|progressista|lulopetista|lulista)\b|\bmito\b|\bodeio\b|\bdetesto\b'
    r'|\bfora (lula|bolsonaro|flavio|pt)\b|\b(lula|flavio|bolsonaro) (13|22|sempre|la)\b|\bamo (o|a) (lula|flavio|bolsonaro|pt)\b')
ORACOES = re.compile(r'([,.!?;:\n]+)')
EXTENSO = (r'(um|uma|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|quinze|vinte|trinta|quarenta|'
           r'cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|duzentos|trezentos|quinhentos|mil)')
# Dinheiro: moeda com número, número com sufixo de valor, e valor por extenso.
VALOR = re.compile(
    rf'(R\s?\$|US\s?\$|U\$|BRL|USD|€|\$)\s?\d[\d.,]*(\s?(mil|milh[õo]es|milh[ãa]o|mi|k|bi))?'
    rf'|\b\d[\d.,]*\s?(k|mil|milh[õo]es|milh[ãa]o|mi|bi|paus|pila|contos?|reais|d[óo]lares|euros)\b(\s+(e\s+)?{EXTENSO}\b)*'
    rf'|\b{EXTENSO}(\s+(e\s+)?{EXTENSO})*\s+(mil|milh[õo]es|milh[ãa]o)\b(\s+(e\s+)?{EXTENSO})*(\s+(de\s+)?reais)?', re.I)
# Número solto numa oração que fala do próprio dinheiro ("minha renda é 7000"). Poupa ano, data, %, pontos e contratos.
DINHEIRO = re.compile(r'\b(tenho|tinha|guardei|juntei|ganho|recebo|recebi|herdei|sal[áa]rio|reserva|invisto|investir|aplicar|'
                      r'aplico|coloco|boto|patrim[ôo]nio|economizei|capital|renda|fgts|grana|dinheiro)\b', re.I)
NUMERO_SOLTO = re.compile(r'(?<![\d/.,])\b(?!(19|20)\d\d\b)\d[\d.,]*\b(?![\d/]|\s*(%|pontos?|contratos?|º|ª|o turno|p\.p\.))')


def _sem_voto(texto: str) -> tuple[str, bool]:
    partes = ORACOES.split(texto)
    achou = False
    for i in range(0, len(partes), 2):
        if POLITICO.search(simples(partes[i])):
            partes[i] = (' ' if partes[i][:1].isspace() else '') + '[trecho sobre voto omitido]'
            achou = True
    return ''.join(partes), achou


def sem_dado_pessoal(texto: str) -> str:
    # Se o roteador acha dinheiro em moeda estrangeira ou gasto por mês, todo número solto sai, em qualquer formato
    # ("EUR 80.000", "80.000€", "20 mil USD"): o registro nunca guarda o que entra na conta de câmbio.
    valor, _, gasto, _ = cambio(normalizar(texto))
    texto, _ = _sem_voto(texto)
    texto = VALOR.sub('[valor omitido]', texto)
    if valor is not None or gasto is not None:
        return NUMERO_SOLTO.sub('[valor omitido]', texto)
    partes = ORACOES.split(texto)
    for i in range(0, len(partes), 2):
        if DINHEIRO.search(partes[i]):
            partes[i] = NUMERO_SOLTO.sub('[valor omitido]', partes[i])
    return ''.join(partes)


def falou_de_voto(texto: str) -> bool:
    return _sem_voto(texto)[1]


def leitura_sem_voto(p, pergunta: str) -> dict:
    """O que o roteador leu, sem o candidato quando a pessoa contou o voto (senão dá para reconstruir o voto)."""
    voto = p.voto_informado or falou_de_voto(pergunta)
    return {'mercados': p.mercados, 'candidatos': [] if voto else p.candidatos, 'temas': p.temas, 'proibidos': p.proibidos}


def ia_sem_voto(ia: dict | None, p, pergunta: str) -> dict | None:
    if not ia or not ia.get('leitura'):
        return ia
    voto = p.voto_informado or falou_de_voto(pergunta)
    leitura = {k: v for k, v in ia['leitura'].items() if k != 'voto_informado'}
    if voto:
        leitura['candidatos'] = []
    return {**ia, 'leitura': leitura}


def violacoes_sem_dinheiro(violacoes, p) -> list[dict]:
    """Com a conta de câmbio, o trecho de uma violação pode trazer o valor calculado a partir do dinheiro da pessoa
    ("R$ 847.410"): os dígitos saem."""
    conta = getattr(p, 'conta_cambio', False)
    return [{**asdict(v), 'trecho': re.sub(r'\d', '#', v.trecho) if conta else v.trecho} for v in violacoes]


def registrar(resposta, ia: dict | None = None, uso: dict | None = None, arquivo=ARQUIVO) -> dict:
    p = resposta.pedido
    linha = {
        'quando': datetime.now(FUSO).isoformat(timespec='seconds'),
        'modo': resposta.modo,
        'pergunta': sem_dado_pessoal(resposta.pergunta),
        'roteador': leitura_sem_voto(p, resposta.pergunta),
        # A conta de câmbio leva o dinheiro da pessoa ("Seus 150.000 euros valem..."): essa resposta não fica guardada.
        'resposta': None if p.conta_cambio else resposta.texto,
        'violacoes_na_resposta': violacoes_sem_dinheiro(resposta.violacoes, p),
        'ia': ia_sem_voto(ia, p, resposta.pergunta),
        'uso': uso or {},
    }
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open('a', encoding='utf-8') as f:
        f.write(json.dumps(linha, ensure_ascii=False) + '\n')
    return linha
