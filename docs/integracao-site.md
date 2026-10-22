# Como o site conversa com o agente

> **Desatualizado desde 22/10/2026.** Este guia descreve o protótipo (função `perguntar` e cota de 3 por semana). O site
> do Bruno usa a função `analyze`, chamada pelo `/agent-proxy` dele, com os créditos do site: ver o README deste
> repositório (seção "Site") e o README do site (seção "Ligar o agente real").

Para quem está fazendo o site. O site só fala com o Supabase; o Supabase fala com o agente.

```
site  ──login──▶  Supabase (projeto "Thoran", organização Trade)
site  ──perguntar──▶  função perguntar (o agente roda dentro dela)  ──▶  Claude, só para ler a pergunta (se ligado)
                          │
                          └─ confere login, termos e cota; grava a pergunta e a resposta
```

## O que o site usa

- **URL do projeto:** `https://ainbuvumkglumwodvdok.supabase.co`
- **Chave pública** (publishable): `sb_publishable_20XhJwLUXyrWRF0gVWTy9Q_HBiUIKJR`. Pode ir no código do site; também está no painel, em Project Settings → API Keys.
- **Nunca no site:** a chave secreta (secret / service_role) e a chave da Anthropic. Elas ficam só no Supabase.

```ts
import { createClient } from '@supabase/supabase-js'
export const supabase = createClient('https://ainbuvumkglumwodvdok.supabase.co', CHAVE_PUBLICA)
```

Um exemplo que funciona, em HTML puro, está em `docs/teste-site/index.html` (login, termos, cota e pergunta).

## 1. Login por e-mail (link mágico)

```ts
await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: 'https://SEU-DOMINIO/entrar' } })
```

No painel: Authentication → URL Configuration. Ponha o domínio do site em **Site URL** e em **Redirect URLs**. Para teste local já estão liberados `http://127.0.0.1:3333` e `http://localhost:3333`.

**Antes de abrir para gente de fora:** configure um SMTP próprio (Authentication → Emails → SMTP Settings). Sem isso, o Supabase só manda o link para quem é do time do projeto, e com limite baixo por hora. Teste com um e-mail de fora do time.

## 2. Termos de uso: antes da primeira pergunta

Mostre os termos de uso e a política de privacidade. Quando a pessoa aceitar:

```ts
await supabase.rpc('aceitar_termos')
```

Sem isso, a função `perguntar` devolve o código `termos`.

## 3. Cota da semana

```ts
const { data } = await supabase.rpc('minha_cota')
// { plano: 'gratis', limite: 3, usadas: 1, aceitou_termos: true }
```

O plano grátis tem 3 perguntas a cada 7 dias (janela móvel). O plano pago só muda pelo servidor.

## 4. Perguntar

```ts
import { FunctionsHttpError } from '@supabase/supabase-js'

const { data, error } = await supabase.functions.invoke('perguntar', { body: { pergunta } })
if (error instanceof FunctionsHttpError) {
  const corpo = await error.context.json().catch(() => null)  // { error, code }; pode vir sem code se o erro for do gateway
  // mostre corpo?.error, ou "Algo deu errado, tente de novo."
} else if (error) {
  // sem conexão, CORS ou tempo esgotado: "Sem conexão. Tente de novo."
} else {
  const r = data.data  // { id, criada_em, texto, texto_curto, modo, cota }
}
```

| `code` | HTTP | Quando |
|---|---|---|
| `sem_login` | 401 | sem login |
| `pergunta_invalida` | 400 | vazia ou com mais de 1.000 caracteres |
| `termos` | 403 | não aceitou os termos |
| `cota` | 429 | já usou as perguntas da semana (vem junto a `cota`) |
| `agente` | 502 | o agente falhou; tente de novo |
| `configuracao` | 503 | a função está sem as chaves do projeto (não deve acontecer) |
| `perfil`, `registro` | 500 | erro do lado do servidor |

Se o agente falhar (`agente`), a pergunta não conta na cota.

A resposta costuma levar de 1 a 3 segundos, e uns 5 a 10 com a leitura pela IA ligada. Mostre um "pensando…".

## 5. Histórico

```ts
const { data } = await supabase.from('perguntas')
  .select('id, criada_em, pergunta, resposta_curta, resposta')
  .eq('status', 'respondida')
  .order('criada_em', { ascending: false }).limit(20)
```

Cada pessoa só vê as próprias perguntas. Antes de gravar, o agente tenta tirar da pergunta o valor em reais e o voto (por exemplo, "Tenho R$ 5 mil" vira "Tenho [valor omitido]"). Mesmo assim, não peça esses dados na tela.

## Como mostrar a resposta (regra legal, não é gosto)

- `texto_curto` (no histórico, `resposta_curta`) é o que aparece primeiro: aviso, as 3 linhas, o risco do mercado, o fecho e as fontes. Mostre inteiro.
- `texto` é a resposta completa, em Markdown, para o "ver detalhes": aviso, recusa, os blocos com fonte, limitações e fontes (links clicáveis).
- Não corte nem reescreva nenhum dos dois. Os textos vêm prontos da base de dados e já passaram pelo filtro legal.
- Não pode ter na tela:
  - botão de comprar ou vender;
  - ranking ou placar de alta e baixa por ativo;
  - alerta, sinal ou notificação de "hora de operar";
  - contagem regressiva, depoimento de lucro ou "a IA acerta X%";
  - link, banner, cupom ou afiliado de corretora, exchange, casa de aposta ou mercado de previsão;
  - cotação ou widget de mercado de previsão (Polymarket, Kalshi e afins);
  - chamada de "IA que prevê o mercado", "aprenda a lucrar" ou parecida, no site ou na página de entrada.
- Não peça no cadastro renda, patrimônio, perfil de investidor nem em quem a pessoa vota.
- No rodapé: quem é a empresa (nome e CNPJ), que ela não é analista credenciada nem consultora autorizada pela CVM, e o link para os termos.
- Antes de abrir ao público ou cobrar: parecer de advogado de mercado de capitais.

As regras completas estão na nota "Regras do agente — o que a IA pode e não pode dizer", no cofre do Obsidian do João.
