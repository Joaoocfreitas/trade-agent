"""Decide o que uma captura é: texto útil, paywall, bloqueio ou erro. Bloqueio não se contorna: vira pendência para o João."""
import re

from .config import PALAVRAS_MINIMAS
from .nomes import norm

PAYWALL = ('exclusivo para assinantes', 'conteudo exclusivo', 'assine para continuar', 'para continuar lendo',
           'ja e assinante', 'faca login para continuar', 'subscribe to continue', 'subscribe to read',
           'for subscribers', 'sign in to continue', 'to continue reading')
DESAFIO_ROBO = ('just a moment', 'verify you are human', 'captcha', 'access denied', 'attention required',
                'are you a robot', 'acesso negado')
HTTP_BLOQUEIO = frozenset({401, 403, 429, 451, 503})
LINK_RE = re.compile(r'!?\[([^\]]*)\]\([^)]*\)')
CORPO_MAXIMO_DE_PREVIA = 600

MOTIVOS = {
    'ok': 'texto completo',
    'paywall': 'paywall: só assinante lê',
    'curto': 'pouco texto: provável paywall desenhado por JavaScript',
    'bloqueado_robots': 'o robots.txt do site não permite robô',
    'bloqueado': 'o site recusou o robô',
    'erro_http': 'página não encontrada ou erro do site',
    'erro': 'falha de rede ou de leitura',
}


def palavras(texto: str) -> int:
    return len(texto.split())


def palavras_corpo(texto: str) -> int:
    """Palavras do corpo: ignora linha que é só link ("veja também", "mais lidas", menus)."""
    n = 0
    for linha in texto.splitlines():
        if LINK_RE.search(linha) and len(re.findall(r'\w+', LINK_RE.sub('', linha))) < 4:
            continue
        n += len(LINK_RE.sub(r'\1', linha).split())
    return n


def classificar_captura(texto: str, http: int | None, erro: str | None) -> str:
    corpo = palavras_corpo(texto)
    t = norm(texto[:40000])
    if erro and 'robots' in erro.lower():
        return 'bloqueado_robots'
    if http in HTTP_BLOQUEIO:
        return 'bloqueado'
    if corpo < 300 and any(d in t for d in DESAFIO_ROBO):
        return 'bloqueado'
    if http is not None and http >= 400:
        return 'erro_http'
    if erro:
        return 'erro'
    if corpo < CORPO_MAXIMO_DE_PREVIA and any(p in t for p in PAYWALL):
        return 'paywall'
    if corpo < PALAVRAS_MINIMAS:
        return 'curto'
    return 'ok'
