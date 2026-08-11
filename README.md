# atendimento-ia

Automação de pós-venda e análise de anúncios do Mercado Livre, usando a API do
Mercado Livre, a API da Anthropic e o n8n como orquestrador.

São duas partes que nasceram em momentos diferentes.

---

## 1. Respondedor de perguntas (pós-venda)

Fluxo orientado a evento: o comprador pergunta num anúncio, o Mercado Livre
dispara um webhook, o n8n recebe o payload, monta o prompt com as
especificações do produto, chama a API da Anthropic e devolve a resposta para a
API do Mercado Livre por HTTP POST.

```text
Mercado Livre  ──webhook──►  n8n  ──prompt──►  API Anthropic
   (pergunta)                 │                      │
        ▲                     └──── resposta ────────┘
        └────────────── HTTP POST ─────────────────────
```

Autenticação em OAuth 2.0 (authorization code + refresh token), estado
trafegando em JSON.

---

## 2. Pipeline de análise de anúncios

A primeira versão fazia a análise dentro do próprio n8n. Ela foi descartada, e
o motivo é a parte mais útil deste repositório:

- **A conversão estava inflada de 4 a 6 vezes.** O fluxo dividia as vendas
  acumuladas do anúncio pelas visitas dos últimos 30 dias. São janelas
  diferentes, então a conta não significava nada. Pior: as recomendações saíam
  em cima desse número.
- **Só olhava a primeira foto** de cada anúncio, e ainda assim sugeria mudanças
  na galeria — várias vezes recomendando algo que já existia na foto 3.
- **A saída era texto livre**, diferente a cada rodada, impossível de tabular.

A versão atual separa as responsabilidades: **o n8n coleta, um script local
analisa.**

```text
n8n (Code node)        ──►  dados_conta.json   todas as imagens, ficha, descrição, preço
relatórios do painel   ──►  planilha .xlsx     métricas REAIS: visitas, vendas, conversão
                                   │
                                   ▼
                             analista.py  ──►  API Anthropic (visão, imagens em base64)
                                   │
                                   ├──►  saida/plano_por_anuncio.md
                                   └──►  saida/plano_conta.md
```

Decisões que sustentam o resultado:

- **O script nunca recalcula conversão.** A métrica vem do relatório oficial do
  Mercado Livre e é injetada no prompt. Número que o modelo não pode inventar.
- **Todas as fotos vão para o modelo**, em base64, porque o CDN do ML
  (`mlstatic.com`) não é acessível por URL a partir da API.
- **Schema fixo de saída (JSON Schema)**, para o resultado dos anúncios virar
  tabela em vez de texto para garimpar.

### O que a primeira rodada completa encontrou

Em 37 anúncios:

- 20 anúncios ativos com **zero visita** — cerca de R$ 23,6 mil de catálogo
  invisível;
- 4 grupos de anúncios duplicados fragmentando tráfego (um deles dividia 968
  visitas entre 3 anúncios do mesmo produto pelo mesmo preço);
- consumíveis convertendo sem tráfego, e máquinas com tráfego e sem conversão.

---

## Como rodar

```bash
cd ml_pipeline
pip install -r requirements.txt

export ANTHROPIC_API_KEY=...
export ML_CONTA="nome da sua conta"
export ML_PERFIL_CATALOGO="o que a conta vende, em uma linha"

python analista.py --limite 3     # rodada de teste
python analista.py                # rodada completa
```

A coleta acontece antes, no n8n: use o conteúdo de
`ml_pipeline/n8n_coletor_code_node.js` num node **Code**, em modo "Run Once for
All Items". O passo a passo está em `ml_pipeline/PASSO_A_PASSO_N8N.md`.

## Estrutura

| Arquivo | O que faz |
|---|---|
| `ml_pipeline/analista.py` | Análise com visão, schema fixo, geração dos planos |
| `ml_pipeline/coletor.py` | Coleta via API do Mercado Livre, fora do n8n |
| `ml_pipeline/ml_auth.py` | OAuth 2.0: authorization code e refresh token |
| `ml_pipeline/n8n_coletor_code_node.js` | Code node do n8n que monta o `dados_conta.json` |
| `ml_pipeline/PASSO_A_PASSO_N8N.md` | Como configurar o fluxo no n8n |

## Credenciais

Nada de credencial neste repositório. Os scripts leem tudo de arquivo local
(`tokens.json`, `credentials.json`, `dados_conta.json`), todos ignorados pelo
`.gitignore`, junto com seus backups. `ANTHROPIC_API_KEY` vem do ambiente.

## Nota

Os planos gerados e os dados coletados são de uma conta real e não estão
publicados aqui. O que está no repositório é o código.
