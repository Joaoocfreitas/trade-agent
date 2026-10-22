"""Busca e lê feeds RSS/Atom: é o jeito mais leve e mais educado de acompanhar uma fonte."""
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import httpx
from bs4 import BeautifulSoup

from .config import FEEDS_SIMULTANEOS, FUSO, ITENS_POR_FEED, MAX_BYTES_FEED
from .fontes import Alvo
from .rede import Bloqueado, PorHost, baixar
from .robots import Robots


@dataclass
class ItemFeed:
    fonte: str
    categoria: str
    acesso: str
    feed_url: str
    url: str
    titulo: str
    resumo: str
    publicado: str | None
    podcast: bool


REDIRECIONADOR_RE = re.compile(r'\*(https?://\S+)$')


def desembrulhar(link: str) -> str:
    """Alguns feeds (Folha) mandam o link por um redirecionador: redir.../*https://site/materia. Vale o endereço real."""
    m = REDIRECIONADOR_RE.search(link)
    return m.group(1) if m else link


def _texto_limpo(html: str, limite: int = 500) -> str:
    texto = ' '.join(BeautifulSoup(html or '', 'html.parser').get_text(' ').split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + '…'


def _data(entry) -> str | None:
    """Data de publicação no horário de Brasília (o feedparser entrega em UTC)."""
    t = entry.get('published_parsed') or entry.get('updated_parsed')
    if not t:
        return None
    try:
        return datetime(*t[:6], tzinfo=timezone.utc).astimezone(FUSO).isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def _link(e) -> str:
    """Episódio de podcast muitas vezes não tem <link>: aí vale o id (se for URL) ou o arquivo de áudio."""
    candidatos = [e.get('link'), e.get('id')] + [x.get('href') for x in e.get('enclosures', [])]
    for c in candidatos:
        c = desembrulhar((c or '').strip())
        if c.startswith('http'):
            return c
    return ''


def ler_feed(conteudo: bytes, alvo: Alvo, limite: int = ITENS_POR_FEED) -> list[ItemFeed]:
    d = feedparser.parse(conteudo)
    itens = []
    for e in d.entries[:limite]:
        link = _link(e)
        if not link:
            continue
        audio = any((x.get('type') or '').startswith('audio') for x in e.get('enclosures', []))
        itens.append(ItemFeed(
            fonte=alvo.fonte, categoria=alvo.categoria, acesso=alvo.acesso, feed_url=alvo.url, url=link,
            titulo=' '.join((e.get('title') or '(sem título)').split()),
            resumo=_texto_limpo(e.get('summary') or e.get('description') or ''),
            publicado=_data(e),
            podcast=audio or 'itunes_duration' in e,
        ))
    return itens


async def buscar_feeds(alvos: list[Alvo], cliente: httpx.AsyncClient, robots: Robots,
                       por_host: PorHost) -> tuple[list[ItemFeed], list[dict]]:
    sem = asyncio.Semaphore(FEEDS_SIMULTANEOS)
    itens: list[ItemFeed] = []
    falhas: list[dict] = []

    def falha(alvo: Alvo, status: str, detalhe: str | None = None) -> None:
        falhas.append({'fonte': alvo.fonte, 'url': alvo.url, 'status': status, 'detalhe': detalhe})
        print(f"  feed ✗ {alvo.fonte}: {status}{f' ({detalhe})' if detalhe else ''}", flush=True)

    async def um(alvo: Alvo) -> None:
        async with sem:
            try:
                status, corpo, _ = await baixar(cliente, alvo.url, robots, por_host, MAX_BYTES_FEED)
            except Bloqueado:
                return falha(alvo, 'bloqueado_robots')
            except Exception as e:  # rede, tempo, tamanho: este feed falha, a rodada segue
                return falha(alvo, 'erro', type(e).__name__)
            if status >= 400:
                return falha(alvo, 'bloqueado' if status in (401, 403, 429, 451, 503) else 'erro_http', str(status))
            try:
                lidos = ler_feed(corpo, alvo)
            except Exception as e:
                return falha(alvo, 'erro', f'feed ilegível ({type(e).__name__})')
            if not lidos:
                return falha(alvo, 'erro', 'feed vazio ou inválido')
            itens.extend(lidos)
            print(f'  feed ✓ {alvo.fonte}: {len(lidos)} itens', flush=True)

    await asyncio.gather(*(um(a) for a in alvos), return_exceptions=True)
    return itens, falhas
