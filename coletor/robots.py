"""robots.txt segundo a RFC 9309 (parser protego, o mesmo do Scrapy), checado com o nome do robô.

Vale para feeds, artigos e páginas. Na dúvida (servidor fora, 429, falha de rede), não entra.
"""
import asyncio
from urllib.parse import urlparse

import httpx
from protego import Protego

from .config import ROBO, TIMEOUT_S


def interpretar(status: int | None, texto: str) -> Protego | bool:
    """2xx: vale o arquivo. 4xx (menos 429): não há regra, pode. 429, 5xx ou falha de rede: não pode."""
    if status is not None and 200 <= status < 300:
        return Protego.parse(texto)
    if status is not None and 400 <= status < 500 and status != 429:
        return True
    return False


class Robots:
    def __init__(self, cliente: httpx.AsyncClient, por_host=None, agente: str = ROBO):
        self.cliente = cliente
        self.por_host = por_host
        self.agente = agente
        self._regras: dict[str, Protego | bool] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def permite(self, url: str) -> bool:
        p = urlparse(url)
        if p.scheme not in ('http', 'https') or not p.netloc:
            return False
        base = f'{p.scheme}://{p.netloc}'
        async with self._locks.setdefault(base, asyncio.Lock()):
            if base not in self._regras:
                self._regras[base] = await self._buscar(base)
        regra = self._regras[base]
        return regra if isinstance(regra, bool) else regra.can_fetch(url, self.agente)

    async def _buscar(self, base: str) -> Protego | bool:
        try:
            async with asyncio.timeout(TIMEOUT_S):
                if self.por_host:
                    async with self.por_host.vez(base):
                        r = await self.cliente.get(f'{base}/robots.txt', follow_redirects=True)
                else:
                    r = await self.cliente.get(f'{base}/robots.txt', follow_redirects=True)
            return interpretar(r.status_code, r.text)
        except (httpx.HTTPError, TimeoutError):
            return interpretar(None, '')
