"""Guarda o que foi coletado: um índice JSONL (dedupe entre rodadas) e o texto completo em Markdown."""
import fcntl
import json
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from .config import MAX_TENTATIVAS
from .nomes import hash_texto, id_url, slug

HTTP_PASSAGEIRO = frozenset({429, 503})


def passageiro(reg: dict) -> bool:
    """Falha que vale tentar de novo numa próxima rodada (rede, servidor ocupado)."""
    return reg['status'] == 'erro' or (reg['status'] == 'bloqueado' and reg.get('http') in HTTP_PASSAGEIRO)


@contextmanager
def trava(raiz: Path):
    """Impede duas coletas ao mesmo tempo (dobraria a carga nos sites e duplicaria o índice)."""
    raiz.mkdir(parents=True, exist_ok=True)
    with open(raiz / '.trava', 'w') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('já há uma coleta rodando (dados/coleta/.trava); espere ela terminar')
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


class Armazem:
    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.indice = raiz / 'itens.jsonl'
        self._finais: set[str] = set()
        self._tentativas: Counter[str] = Counter()
        self._hash_pagina: dict[tuple[str, str], str] = {}
        for reg in self.registros():
            self._lembrar(reg)

    def registros(self) -> list[dict]:
        """Lê o índice pulando linha corrompida (rodada interrompida no meio da gravação)."""
        if not self.indice.exists():
            return []
        regs, ruins = [], 0
        with self.indice.open(encoding='utf-8') as f:
            for linha in f:
                if not linha.strip():
                    continue
                try:
                    regs.append(json.loads(linha))
                except json.JSONDecodeError:
                    ruins += 1
        if ruins:
            print(f'aviso: {ruins} linha(s) corrompida(s) ignorada(s) em {self.indice}', file=sys.stderr)
        return regs

    def _lembrar(self, reg: dict) -> None:
        if passageiro(reg):
            self._tentativas[reg['url']] += 1
        else:
            self._finais.add(reg['url'])
        if reg['tipo'] == 'pagina' and reg.get('hash'):
            self._hash_pagina[(reg['fonte'], reg['url'])] = reg['hash']

    def ja_visto(self, url: str) -> bool:
        return url in self._finais or self._tentativas[url] >= MAX_TENTATIVAS

    def pagina_mudou(self, fonte: str, url: str, texto: str) -> bool:
        return self._hash_pagina.get((fonte, url)) != hash_texto(texto)

    def salvar(self, registro: dict, texto: str | None = None) -> dict:
        """Grava o texto (se houver) e acrescenta o registro ao índice. Devolve o registro com o caminho do arquivo."""
        reg = dict(registro)
        if texto:
            reg['hash'] = hash_texto(texto)
            dia = (reg.get('publicado') or reg['coletado_em'])[:10]
            arq = (self.raiz / 'textos' / reg['categoria'] / slug(reg['fonte'])
                   / f"{dia}-{slug(reg['titulo'], 50)}-{id_url(reg['url'])[:8]}.md")
            arq.parent.mkdir(parents=True, exist_ok=True)
            cabeca = '\n'.join(f'{k}: {json.dumps(reg.get(k), ensure_ascii=False)}'
                               for k in ('fonte', 'categoria', 'tipo', 'url', 'titulo', 'publicado', 'coletado_em',
                                         'status', 'assuntos'))
            arq.write_text(f'---\n{cabeca}\n---\n\n{texto}\n', encoding='utf-8')
            reg['arquivo'] = str(arq.relative_to(self.raiz))
        self.raiz.mkdir(parents=True, exist_ok=True)
        with self.indice.open('a+', encoding='utf-8') as f:
            f.seek(0, 2)
            if f.tell() > 0:  # se a última gravação foi interrompida sem '\n', não cola na linha quebrada
                f.seek(f.tell() - 1)
                if f.read(1) != '\n':
                    f.write('\n')
            f.write(json.dumps(reg, ensure_ascii=False) + '\n')
        self._lembrar(reg)
        return reg
