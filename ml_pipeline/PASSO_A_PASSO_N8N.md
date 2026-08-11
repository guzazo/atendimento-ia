# Passo a passo no n8n — gerar o `dados_conta.json`

O workflow novo é **muito mais simples** que o antigo. Só 5 nodes:

```
Trigger  →  HTTP Request1 (OAuth)  →  Code (coletor)  →  Convert to File  →  Read/Write Files
                                                                                    ↓
                                                              ml_pipeline/dados_conta.json
```

Tudo que vinha depois no workflow antigo (Split Out, Merge, Filter, HTTP Request7/8, Extract from File)
**não é mais necessário** — a análise agora é o `analista.py`.

---

## Passo 0 — Ligar o n8n

No Terminal:

```bash
N8N_USER_FOLDER=/Users/guzazo/atendimento-ia/n8n N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=False WEBHOOK_URL=http://localhost:5678/ N8N_SECURE_COOKIE=False N8N_PROXY_HOPS=1 nohup /opt/homebrew/opt/node@22/bin/node /opt/homebrew/lib/node_modules/n8n/bin/n8n start > ~/atendimento-ia/n8n/n8n-native.log 2>&1 & disown
```

Espere ~20s e abra **http://localhost:5678** no navegador. (Não precisa de túnel Cloudflare — é local.)

---

## Passo 1 — Criar um workflow novo (não mexa no antigo)

1. No n8n, clique em **Workflows** → **Create Workflow** (canto superior direito).
2. Nomeie: `Coletor ML`.

Vamos deixar o workflow antigo intacto como backup.

---

## Passo 2 — Copiar o node de OAuth do workflow antigo

O único node que vale reaproveitar é o do token (ele já tem seu client_id/secret/refresh_token).

1. Abra o workflow **antigo**.
2. Clique no node **HTTP Request1** (o do token, `oauth/token`) para selecioná-lo.
3. **Cmd+C**.
4. Volte para o workflow **Coletor ML** e dê **Cmd+V**.

⚠️ **O nome do node precisa continuar exatamente `HTTP Request1`** — o código do coletor referencia
`$('HTTP Request1')`. Se colar e o n8n renomear para "HTTP Request2" ou similar, clique duas vezes no
node, renomeie de volta para `HTTP Request1`.

---

## Passo 3 — Adicionar o Trigger

1. No canvas, clique no **+** e busque **Manual Trigger** ("When clicking 'Execute workflow'").
2. Conecte: **Trigger → HTTP Request1**.

---

## Passo 4 — Adicionar o node Code (o coletor)

1. Clique no **+** depois do HTTP Request1 e busque **Code**.
2. Em **Mode**, escolha **Run Once for All Items**.
3. Em **Language**, deixe **JavaScript**.
4. Apague o código de exemplo e **cole todo o conteúdo** de `ml_pipeline/n8n_coletor_code_node.js`.
5. Conecte: **HTTP Request1 → Code**.

⚠️ A conexão no canvas é obrigatória — sem ela, `$('HTTP Request1')` dá erro
(`createNoConnectionError`), mesmo com o nome certo.

---

## Passo 5 — Salvar direto no disco (evita travar o navegador)

O n8n roda nativo no Mac, então ele consegue escrever direto na pasta do projeto.
Isso evita o problema de copiar JSON gigante pela interface (que travou da última vez).

**Node A — Convert to File**
1. Clique no **+** depois do Code e busque **Convert to File**.
2. **Operation:** `Convert to JSON`
3. **Mode:** `All Items to One File`
4. **Put Output in Field:** `data`

**Node B — Read/Write Files from Disk**
1. Clique no **+** depois do Convert to File e busque **Read/Write Files from Disk**.
2. **Operation:** `Write File to Disk`
3. **File Path and Name:** `/Users/guzazo/atendimento-ia/ml_pipeline/dados_conta.json`
4. **Input Binary Field:** `data`

Ficando: **Code → Convert to File → Read/Write Files from Disk**.

---

## Passo 6 — Executar

Clique em **Execute Workflow** (botão no rodapé).

- Vai demorar 1–3 min (ele busca detalhes + descrição + perguntas de cada um dos ~25 anúncios).
- No fim, o arquivo `ml_pipeline/dados_conta.json` estará no disco.

Para conferir no Terminal:
```bash
ls -lh /Users/guzazo/atendimento-ia/ml_pipeline/dados_conta.json
```

---

## Passo 7 — ⚠️ ROTACIONAR O REFRESH_TOKEN (não pule!)

**Cada execução do HTTP Request1 consome o refresh_token e devolve um NOVO.**
Se você não atualizar, a próxima execução falha com `invalid_grant`.

1. Clique no node **HTTP Request1**.
2. Na aba **OUTPUT**, copie o valor de `refresh_token` (o novo).
3. Abra os parâmetros do node e **cole esse valor no campo `refresh_token`** (substituindo o antigo).
4. **Salve o workflow** (Cmd+S).

Faça isso **depois de toda execução**.

---

## Passo 8 — Rodar o analista

No Terminal:

```bash
cd /Users/guzazo/atendimento-ia/ml_pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=...        # sua chave da Anthropic

python analista.py --limite 3       # testa com 3 anúncios
python analista.py                  # roda todos
```

Saída em `ml_pipeline/saida/`.

---

## Se der erro

| Erro | Causa | Solução |
|---|---|---|
| `invalid_grant` no HTTP Request1 | refresh_token velho | Passo 7 — cole o refresh_token novo |
| `createNoConnectionError` | Code não está ligado no HTTP Request1 | Conecte os nodes no canvas |
| `Referenced node doesn't exist` | node não se chama `HTTP Request1` | Renomeie o node de OAuth |
| `403 PA_UNAUTHORIZED_RESULT_FROM_POLICIES` | bug do node HTTP Request nativo | Não deve ocorrer: o coletor usa `this.helpers.httpRequest` dentro do Code, que não tem esse bug |
| `ERRO: nenhum anúncio encontrado` no analista.py | JSON vazio ou formato inesperado | Confira se o `dados_conta.json` tem a chave `items` |
