"""Lê as fontes verificadas (JSON da pesquisa) e decide o que o coletor busca em cada uma."""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .config import ACESSOS_COLETAVEIS, CATEGORIAS
from .nomes import norm, titulo_nota

URL_RE = re.compile(r'https?://[^\s,;)"\'<>\]]+')
FEED_HOSTS = ('feeds.', 'feed.', 'rss.')
FEED_PATH_RE = re.compile(r'(feed|rss|atom|\.xml)', re.I)


@dataclass(frozen=True)
class Alvo:
    fonte: str  # título da nota da fonte no cofre
    categoria: str
    acesso: str
    tipo: str  # 'feed' | 'pagina'
    url: str


def _encaixa(fonte: dict) -> bool:
    """Pessoa mora em pessoas_*; veículo, programa ou dado mora fora."""
    return (fonte.get('tipo') == 'pessoa') == fonte['categoria'].startswith('pessoas_')


def preferir(atual: dict, nova: dict) -> bool:
    """A mesma fonte veio de duas categorias: troca só se a nova encaixa no tipo e a atual não."""
    return _encaixa(nova) and not _encaixa(atual)


def carregar_fontes(pasta: Path) -> list[dict]:
    """Junta os JSON das categorias e os acréscimos do crítico, sem duplicar nomes."""
    por_chave: dict[str, dict] = {}
    arquivos = [pasta / f'{k}.json' for k in CATEGORIAS] + [pasta / 'acrescimos.json']
    for arq in arquivos:
        if not arq.exists():
            continue
        for it in json.loads(arq.read_text(encoding='utf-8'))['itens']:
            cat = it.get('categoria') or arq.stem
            if cat not in CATEGORIAS:
                continue
            nova = {**it, 'categoria': cat, 'titulo': titulo_nota(it['nome'])}
            chave = norm(nova['titulo'])
            if chave not in por_chave or preferir(por_chave[chave], nova):
                por_chave[chave] = nova
    return list(por_chave.values())


def eh_feed(url: str) -> bool:
    p = urlparse(url)
    return p.netloc.startswith(FEED_HOSTS) or bool(FEED_PATH_RE.search(p.path + '?' + p.query))


def extrair_feeds(fonte: dict) -> list[str]:
    texto = ' '.join((fonte.get('url', ''), fonte.get('acesso_detalhe', ''), fonte.get('o_que_extrair', '')))
    urls = (u.rstrip('.') for u in URL_RE.findall(texto))
    return list(dict.fromkeys(u for u in urls if eh_feed(u)))


def selecionar_alvos(fontes: list[dict], categoria: str | None = None) -> list[Alvo]:
    """Feed quando a fonte tem; senão, a página principal. Só fontes públicas ou parcialmente públicas."""
    alvos = []
    for f in fontes:
        if f['acesso'] not in ACESSOS_COLETAVEIS or (categoria and f['categoria'] != categoria):
            continue
        feeds = extrair_feeds(f)
        if feeds:
            alvos += [Alvo(f['titulo'], f['categoria'], f['acesso'], 'feed', u) for u in feeds]
        elif f.get('url', '').startswith('http'):
            alvos.append(Alvo(f['titulo'], f['categoria'], f['acesso'], 'pagina', f['url'].strip()))
    return alvos
