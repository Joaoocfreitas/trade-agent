# trade-agent

O código do mega brain de trade. O cérebro em si (as notas) vive no Obsidian, em `~/Documents/trade-obsidian/Trade`.

## O que tem aqui

| Pasta | O quê |
|---|---|
| `coletor/` | Lê as fontes verificadas, busca os feeds RSS e captura com o [crawl4ai](https://github.com/unclecode/crawl4ai) o texto completo dos artigos e das páginas públicas. Grava o texto em `dados/coleta/` e um resumo por coleta no cofre (`10 Coleta/`). |
| `scripts/gerar_cofre.py` | Gera as notas de fonte, os índices, o checklist do que o João passa e as notas de evento a partir de `dados/fontes/`. |
| `dados/fontes/` | Saída da pesquisa verificada de 21/10/2026 (uma lista JSON por categoria, a linha do tempo e o caso do 1º turno). |
| `dados/coleta/` | O que o coletor trouxe. Fica fora do git. |
| `estudo/` | Fase 2: baixa as séries oficiais e mede a reação a cada evento (−5 a +5 pregões). Resultado em `dados/estudo/` e na nota "Estudo de evento 2016–2026" do cofre. O Yahoo ficou de fora porque o robots.txt dele proíbe robô. |

## Comandos

```bash
cd ~/Documents/trade-agent
.venv/bin/python -m coletor listar                  # o que será buscado, por categoria
.venv/bin/python -m coletor coletar                 # feeds + 3 artigos completos por feed (~5 min)
.venv/bin/python -m coletor coletar --paginas       # + retrato das páginas sem feed (~15 min, 1x por semana)
.venv/bin/python -m coletor coletar --artigos 0     # só manchetes, rapidinho
.venv/bin/python scripts/gerar_cofre.py             # regenera as notas de fonte no cofre
.venv/bin/python -m estudo baixar                   # Fase 2: séries oficiais (Ipeadata, BCB, Tesouro, Focus)
.venv/bin/python -m estudo medir                    # Fase 2: mede os 50 eventos e grava dados/estudo/
.venv/bin/python -m pytest -q                       # testes
```

## Regras do robô (não mudar sem conversar)

- Identifica-se como robô (`TradeAgentPesquisa`) e **respeita o robots.txt** (RFC 9309, parser protego, com o nome do robô) nos feeds, nos artigos e nas páginas, **em cada salto de redirecionamento**. Na dúvida (5xx, 429, falha de rede), não entra.
- **Sem modo furtivo**: `enable_stealth`, `magic`, `simulate_user` e `override_navigator` ficam desligados, e a caixa do paywall não é removida. O crawl4ai liga sozinho `--disable-blink-features=AutomationControlled`, que esconde `navigator.webdriver`; `coletor/paginas.py` tira essa flag, e `tests/test_navegador.py` prova que o navegador se mostra automatizado.
- Um pedido por vez a cada domínio (lock segurado durante o pedido), 1,5 s depois do fim do anterior, e no máximo 3 páginas abertas ao mesmo tempo. Não use o `RateLimiter` do crawl4ai para isso: ele não serializa.
- Caso real que a regra pegou: o feed da CNN Brasil redireciona para `admin.cnnbrasil.com.br`, cujo robots.txt proíbe tudo. Fica de fora.
- O que o site não deixa ler (paywall, robots, recusa) vira pendência na nota da coleta, para o João mandar à mão. Não é um problema para contornar.
- Fontes `api_gratis` (BCB, TSE, B3…) não passam pelo crawler: vão para o pipeline de dados da fase 2, por API.

## Instalação do zero

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

O crawl4ai fica fixado em 0.9.5. Ele depende de `unclecode-litellm` (um fork fixado do litellm, criado depois que as versões 1.82.7/1.82.8 do litellm foram comprometidas no PyPI em março de 2026; issues #1864 e #2098 do crawl4ai). Antes de subir de versão, leia o CHANGELOG.
