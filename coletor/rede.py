"""Educação com os sites: um pedido por vez a cada domínio, intervalo entre pedidos e robots.txt em cada salto.

Regra para quem usa: nunca chame `Robots.permite` de dentro de um `PorHost.vez` do mesmo domínio
(o robots.txt também passa pela vez do domínio, e o lock não é reentrante).
"""
import asyncio
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from urllib.parse import urljoin, urlparse

import httpx

from .config import MAX_REDIRECIONAMENTOS, TIMEOUT_S


class PorHost:
    """Um pedido por vez a cada domínio; o intervalo conta a partir do FIM do pedido anterior."""

    def __init__(self, intervalo: float):
        self.intervalo = intervalo
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._fim: dict[str, float] = {}

    @asynccontextmanager
    async def vez(self, url: str):
        host = urlparse(url).netloc.lower()
        async with self._locks[host]:
            espera = self._fim.get(host, 0.0) + self.intervalo - time.monotonic()
            if espera > 0:
                await asyncio.sleep(espera)
            try:
                yield
            finally:
                self._fim[host] = time.monotonic()


class Bloqueado(Exception):
    """O robots.txt de algum salto não deixa o robô entrar."""

    def __init__(self, url: str):
        super().__init__(url)
        self.url = url


async def baixar(cliente: httpx.AsyncClient, url: str, robots, por_host: PorHost, max_bytes: int) -> tuple[int, bytes, str]:
    """GET que segue redirecionamentos à mão, checando o robots.txt de cada salto, com tempo e tamanho limitados.

    O cliente precisa ter follow_redirects=False. Devolve (status, corpo, url final).
    """
    atual = url
    for _ in range(MAX_REDIRECIONAMENTOS + 1):
        if not await robots.permite(atual):
            raise Bloqueado(atual)
        async with por_host.vez(atual):
            # O limite de tempo vale para o pedido, não para a fila do domínio (feeds do mesmo host esperam a vez).
            async with asyncio.timeout(TIMEOUT_S * 3), cliente.stream('GET', atual) as r:
                if r.is_redirect and 'location' in r.headers:
                    proximo = urljoin(atual, r.headers['location'])
                else:
                    corpo = bytearray()
                    async for pedaco in r.aiter_bytes():
                        corpo += pedaco
                        if len(corpo) > max_bytes:
                            raise ValueError(f'resposta maior que {max_bytes} bytes')
                    return r.status_code, bytes(corpo), atual
        atual = proximo
    raise RuntimeError('redirecionamentos demais')


async def resolver(cliente: httpx.AsyncClient, url: str, robots, por_host: PorHost) -> str:
    """Descobre o endereço final com HEAD, salto a salto, checando o robots.txt de cada um. Levanta Bloqueado.

    Se o site não responde a HEAD, devolve o último endereço conhecido; a checagem depois da captura cobre o resto.
    """
    atual = url
    for _ in range(MAX_REDIRECIONAMENTOS):
        if not await robots.permite(atual):
            raise Bloqueado(atual)
        try:
            async with por_host.vez(atual):
                r = await asyncio.wait_for(cliente.head(atual), TIMEOUT_S)
        except (httpx.HTTPError, TimeoutError):
            return atual
        if not (r.is_redirect and 'location' in r.headers):
            return atual
        atual = urljoin(atual, r.headers['location'])
    if not await robots.permite(atual):
        raise Bloqueado(atual)
    return atual
