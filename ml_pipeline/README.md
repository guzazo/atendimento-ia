# Pipeline de análise de anúncios — a conta

Substitui o workflow n8n antigo (que gerava conversão irreal e só via 1 foto).
Arquitetura: **n8n coleta → script local analisa**.

```
n8n (coletor) ─────────────►  dados_conta.json   (todas as imagens, ficha, perguntas, preço)
relatórios ML exportados ──►  Desempenho...xlsx   (métricas REAIS: conversão, visitas, vendas)
Central de Aprendizagem ───►  regras_central.md   (boas práticas do ML condensadas)
                                     │
                                     ▼
                              analista.py ── API Claude (visão) ──► saida/plano_por_anuncio.md
                                                                    saida/plano_conta.md
```

## Por que este pipeline (o antigo não servia)
- **Conversão irreal:** o n8n dividia vendas acumuladas por visitas de 30 dias → inflava 4–6x. Aqui a conversão vem do **relatório real** do ML; o script nunca recalcula.
- **Cego em imagem:** o n8n só baixava a 1ª foto. Aqui o `analista.py` manda **todas** (até `MAX_IMGS_POR_ANUNCIO`) em base64.
- **Saída inconsistente:** agora há um **schema fixo** (JSON Schema) — dá para tabular os 25 sem garimpar texto.
- **Novos planos:** cupons, promoções, kits e estrutura de anúncio saem no `plano_conta.md`.

## Passo a passo

### 1. Coletar os dados no n8n
- Abra o node **Code** com o conteúdo de `n8n_coletor_code_node.js` (modo "Run Once for All Items").
- Ligue-o depois do seu node OAuth (`HTTP Request1`, grant_type=refresh_token — lembre de rotacionar o refresh_token).
- Rode e salve o JSON de saída como `ml_pipeline/dados_conta.json`.

### 2. Exportar as métricas reais do ML
- No ML: Métricas → baixe **"Desempenho dos seus anúncios"** (.xlsx).
- Deixe em `~/Downloads/relatorios ml/Desempenho dos seus anúncios.xlsx` (ou passe `--metricas <caminho>`).

### 3. Rodar o analista
```bash
cd ml_pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=...        # ou: ant auth login
python analista.py --limite 3       # teste com 3 anúncios primeiro
python analista.py                  # roda todos
```

Saída em `ml_pipeline/saida/`:
- `plano_por_anuncio.md` — diagnóstico + ações por anúncio (ordenado do pior pro melhor)
- `plano_conta.md` — cupons, promoções, kits, Full, Ads, Minha Página, preço, catálogo, reputação
- `resultados_brutos.json` / `plano_conta.json` — dados estruturados

## Ajustes (topo do `analista.py`)
- `MODELO` — `claude-sonnet-5` (padrão: melhor equilíbrio custo/qualidade para lote de 25).
  Para máxima capacidade: `claude-opus-4-8`. Para o mais barato: `claude-haiku-4-5`.
- `MAX_IMGS_POR_ANUNCIO` — 5 (capa + 4 infográficos). Menos imagens = mais barato.
- `EFFORT` — `high` (padrão). `medium` reduz custo/latência.
- `MAX_TOKENS` — 12000. Margem para o tokenizador do Sonnet 5 (~30% mais tokens que o 4.6).
  Se algum item falhar com "Resposta truncada", suba este valor ou baixe o `EFFORT`.

## Custo
As regras da Central entram no `system` com **cache**, então a partir do 2º anúncio elas são lidas
do cache (~10% do preço). O grosso do custo são as imagens: 25 anúncios × 5 fotos.
Sonnet 5 ($3/$15 por MTok, com preço promocional $2/$10 até 31/08/2026) mantém a rodada barata.
Rode `--limite 3` primeiro para medir antes de soltar os 25.
