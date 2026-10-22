# trade-agent

O código do mega brain de trade. O cérebro em si (as notas) vive no Obsidian, em `~/Documents/trade-obsidian/Trade`.

## O que tem aqui

| Pasta | O quê |
|---|---|
| `coletor/` | Lê as fontes verificadas, busca os feeds RSS e captura com o [crawl4ai](https://github.com/unclecode/crawl4ai) o texto completo dos artigos e das páginas públicas. Grava o texto em `dados/coleta/` e um resumo por coleta no cofre (`10 Coleta/`). |
| `scripts/gerar_cofre.py` | Gera as notas de fonte, os índices, o checklist do que o João passa e as notas de evento a partir de `dados/fontes/`. |
| `dados/fontes/` | Saída da pesquisa verificada de 21/10/2026 (uma lista JSON por categoria, a linha do tempo e o caso do 1º turno). |
| `dados/coleta/` | O que o coletor trouxe. Fica fora do git. |
| `agente/` | O protótipo do agente de repertório: entende a pergunta (`roteador.py`), monta a resposta só com fatos de `dados/` e fonte em cada número (`fatos.py`, `resposta.py`), barra frase proibida, número sem fonte e falta de aviso (`filtro.py`), e, se houver credencial da API, deixa o Claude classificar a pergunta numa lista fechada, somando à leitura por palavras-chave (`ia.py`). A IA não escreve a resposta. `exportar.py` gera a base de fatos e o gabarito para a versão em TypeScript que roda no Supabase. As regras vêm da nota "Regras do agente" do cofre. Toda conversa vai para `dados/agente/conversas.jsonl` (fora do git), sem valor em reais nem voto. |
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
.venv/bin/python -m agente "Ibovespa se o Flávio ganhar?"  # o agente responde (com IA só se houver credencial)
.venv/bin/python -m agente --sem-ia --curta "..."    # sem IA, só o aviso e as 3 linhas
.venv/bin/python -m agente --bateria                # as perguntas adversariais da nota de regras e o placar
.venv/bin/python -m pytest -q                       # testes
```

## Regras do robô (não mudar sem conversar)

- Identifica-se como robô (`TradeAgentPesquisa`) e **respeita o robots.txt** (RFC 9309, parser protego, com o nome do robô) nos feeds, nos artigos e nas páginas, **em cada salto de redirecionamento**. Na dúvida (5xx, 429, falha de rede), não entra.
- **Sem modo furtivo**: `enable_stealth`, `magic`, `simulate_user` e `override_navigator` ficam desligados, e a caixa do paywall não é removida. O crawl4ai liga sozinho `--disable-blink-features=AutomationControlled`, que esconde `navigator.webdriver`; `coletor/paginas.py` tira essa flag, e `tests/test_navegador.py` prova que o navegador se mostra automatizado.
- Um pedido por vez a cada domínio (lock segurado durante o pedido), 1,5 s depois do fim do anterior, e no máximo 3 páginas abertas ao mesmo tempo. Não use o `RateLimiter` do crawl4ai para isso: ele não serializa.
- Caso real que a regra pegou: o feed da CNN Brasil redireciona para `admin.cnnbrasil.com.br`, cujo robots.txt proíbe tudo. Fica de fora.
- O que o site não deixa ler (paywall, robots, recusa) vira pendência na nota da coleta, para o João mandar à mão. Não é um problema para contornar.
- Fontes `api_gratis` (BCB, TSE, B3…) não passam pelo crawler: vão para o pipeline de dados da fase 2, por API.

## Regras do agente (não mudar sem conversar)

- O agente **não escreve número de cabeça**: todo número vem de `dados/` e sai com a fonte.
- **A IA não escreve texto que a pessoa lê.** No ataque de 22/10/2026, 91% das frases sutis de dica ou direção passaram pelo filtro de padrões; por isso a IA só classifica a pergunta (saída estruturada) e a resposta sai dos blocos da base. As frases e perguntas do ataque viraram teste (`tests/dados/`).
- A recusa, os avisos e o fecho são textos fixos (`agente/textos.py`), copiados da nota de regras. Mudou lá, muda aqui e nos testes.
- O valor em reais e o voto que a pessoa contar não mudam a resposta (`tests/test_agente.py` prova) e não vão para o registro.
- Os candidatos aparecem sempre os dois, no mesmo formato e em ordem alfabética. Pesquisa só entra com número de registro no TSE. Mercado de previsão só aparece como regra, nunca como cotação.
- O modelo vem de `TRADE_AGENTE_MODELO` (padrão `claude-opus-5-5`); o `claude-haiku-5-5` custa cerca de 40 vezes menos por pergunta e basta para classificar.

## Site (Supabase + API)

O site é o do Bruno (`brunoroos71/thoran`). Ele chama a função `analyze` deste repositório pelo `/agent-proxy` dele, que
confere login e créditos. O esquema do banco (tabelas, permissões, `auditoria_agente`) mora no repositório do site.

- `supabase/functions/analyze/`: a API do agente para o site. `POST` com `Authorization: Bearer AGENT_API_KEY` e
  `{ query, market, locale }`; responde o `AnalysisResponse` do site (texto completo, versão curta, cartão dos casos) e
  grava a auditoria em `public.auditoria_agente`.
- `supabase/functions/_shared/agente/`: o agente em TypeScript, a partir de `_shared/base.json` (com os cartões de
  `agente/cartoes.py`). O Python continua dono dos dados e dos testes: `tests/dados/paridade.json` prova que os dois
  respondem igual (`deno test --allow-read --allow-env supabase/functions/_shared/agente/`).
- **Quando os dados mudarem** (Selic, pesquisa, resultado de eleição): `.venv/bin/python -m agente.exportar`, rode os
  testes dos dois lados e publique:
  `npx supabase@2.120.0 functions deploy analyze --project-ref ainbuvumkglumwodvdok --no-verify-jwt --use-api`.
  Se o texto das respostas mudou, o resumo `EXTRAS.respostas` de `_shared/agente/filtro_test.ts` também muda:
  recalcule pelo Python.
- Segredos da função: `AGENT_API_KEY` (o mesmo do site) e, opcionais, `ANTHROPIC_API_KEY` (liga a leitura da pergunta
  pela IA; sem ele, só palavras-chave) e `TRADE_AGENTE_MODELO`.
- `supabase/functions/perguntar/`, `supabase/migrations/` e `docs/teste-site/`: o protótipo de antes do site, a
  aposentar depois que o site estiver no ar.

## Atualização diária (GitHub Actions)

Roda sozinha, no GitHub, com o Mac desligado. Os arquivos estão em `.github/workflows/`.

| Workflow | Quando | O que faz |
|---|---|---|
| Rodada diária (`diaria.yml`) | 07:47 e 21:23 (Brasília) | `python -m estudo diario`: baixa as séries oficiais e o Focus, passa cada uma pelo portão (`estudo/portao.py`), exporta a base, roda os testes e publica a `analyze` se algum dado mudou. |
| Manchetes (`manchetes.yml`) | de 2 em 2 horas, das 07h às 23h | Lê só título e link dos feeds de imprensa. Às 07h abre nas Issues a lista do dia com o que casou um gatilho (`python -m coletor gatilhos`). Nada vai para o usuário. |
| Testes (`testes.yml`) | todo pull request | Exporta e roda Python e TypeScript. |
| Publicar (`publicar.yml`) | merge na `main` | Exporta, testa e publica a `analyze`. |

**O portão.** Série com número estranho não entra: fica a de antes, com a data de antes, e abre a Issue "Rodada diária: série segurada". Ele confere:
- faixa plausível;
- salto máximo de um ponto para o seguinte;
- histórico intacto;
- Selic em múltiplo de 0,25;
- Ibovespa inteiro e só em dia útil.

Calibrado contra 2016–2026, ele só seguraria dias extremos de verdade, como Joesley (2017), a covid (2020) e o dia seguinte ao 1º turno de 2026.

**Liberar depois de conferir na fonte:** Actions › Rodada diária › Run workflow, com as séries em "aceitar" (ex.: `ptax`).

**Ligar ou desligar uma série:** `dados/series/ligadas.json`. O Ibovespa começa desligado até o advogado responder sobre a licença de dados da B3.

**Fato novo** (pesquisa, turno, reunião do Copom, evento): só por pull request, com a fonte primária e um segundo conferente. O merge publica.

**Para publicar sozinho:** o segredo `SUPABASE_ACCESS_TOKEN` em Settings › Secrets and variables › Actions. Sem ele, a rodada guarda o dado e não publica.

## Instalação do zero

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

O crawl4ai fica fixado em 0.9.5. Ele depende de `unclecode-litellm` (um fork fixado do litellm, criado depois que as versões 1.82.7/1.82.8 do litellm foram comprometidas no PyPI em março de 2026; issues #1864 e #2098 do crawl4ai). Antes de subir de versão, leia o CHANGELOG.
