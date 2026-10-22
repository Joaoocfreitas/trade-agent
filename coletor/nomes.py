"""Normalização de nomes: títulos de nota, slugs de arquivo e identificadores estáveis."""
import hashlib
import re
import unicodedata


def norm(s: str) -> str:
    """Minúsculas, sem acento, só letras e números separados por espaço."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def titulo_nota(s: str) -> str:
    """Nome que o Obsidian aceita como arquivo e como [[link]]."""
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()[:120]


def slug(s: str, n: int = 60) -> str:
    return norm(s).replace(' ', '-')[:n].strip('-') or 'sem-titulo'


def id_url(url: str) -> str:
    return hashlib.sha1(url.strip().encode()).hexdigest()[:16]


def hash_texto(texto: str) -> str:
    return hashlib.sha1(' '.join(texto.split()).encode()).hexdigest()[:16]
