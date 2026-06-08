# atendimento-ia
Integração autônoma entre a API do Mercado Livre e Claude Pro (Anthropic) orquestrada via n8n para automação de atendimento pós-venda.

# 🤖 Sistema de Atendimento Inteligente - Mercado Livre & Claude Pro (MCP)

Este projeto apresenta o desenvolvimento e a implementação de uma arquitetura de integração ativa entre a API do Mercado Livre e o modelo de linguagem Claude Pro (Anthropic) [n8n, Dev Center do Mercado Livre]. A solução utiliza o protocolo **Model Context Protocol (MCP)** e a plataforma de automação **n8n** para criar um agente autônomo capaz de processar e responder dúvidas de clientes em tempo real [n8n].

---

## 🚀 Objetivo do Projeto
Demonstrar a aplicação prática de conceitos fundamentais de **Ciência da Computação** (Sistemas Distribuídos, APIs REST, Webhooks e Manipulação de Estruturas de Dados JSON) na automação inteligente de processos de negócios digitais.

---

## 🏗️ Arquitetura do Sistema e Fluxo de Dados

O ecossistema opera de forma orientada a eventos através do seguinte pipeline:

```text
+-------------------+             +-----------+             +------------+

|   Mercado Livre   | --(Webhook)-> |    n8n    | --(Prompt)->| Claude Pro |
| (Nova Pergunta)   |             | (Orquest) |             |  (Agente)  |
+-------------------+             +-----------+             +------------+
          ^                                                       |

          |__________________(HTTP POST Resposta)_________________|
```

1. **Gatilho (Event Trigger):** Um cliente realiza uma pergunta em um anúncio. O Mercado Livre dispara um gatilho de Webhook [Dev Center do Mercado Livre].
2. **Orquestração (n8n):** O servidor n8n recebe a requisição HTTP POST carregando o payload em formato **JSON** [n8n].
3. **Processamento Cognitivo (Claude Pro/MCP):** A inteligência artificial consome as especificações do produto tratadas por parâmetros do sistema e gera uma resposta contextualizada, assertiva e persuasiva.
4. **Ação (HTTP Request):** O fluxo executa um POST de retorno à API do Mercado Livre, publicando a resposta de forma instantânea na plataforma [n8n, Dev Center do Mercado Livre].

---

## 🛠️ Tecnologias e Protocolos Utilizados

*   **Linguagem & Dados:** JSON (JavaScript Object Notation) para transferência de estado.
*   **Protocolo de Comunicação:** HTTP/HTTPS através de arquitetura REST.
*   **Autenticação:** OAuth 2.0 (Authorization Code + Refresh Token) [Dev Center do Mercado Livre].
*   **Orquestrador de Workflow:** n8n (Integração de dados) [n8n].
*   **Motor Cognitivo:** Anthropic Claude Pro com protocolo MCP.

---

## 📂 Estrutura de Arquivos Locais

```text
├── .gitignore              # Proteção de dependências e variáveis de ambiente
├── README.md               # Documentação técnica do projeto
└── workflow-n8n.json       # Arquivo de exportação do fluxo lógico estruturado
```

---

## 🛡️ Segurança e Boas Práticas (SecOps)
Todas as chaves privadas de API (`Client Secret`, `Access Token`, `Anthropic API Key`) são gerenciadas estritamente por meio de variáveis de ambiente locais (`.env`), as quais estão mapeadas no arquivo `.gitignore` para prevenir de forma absoluta o vazamento de credenciais em repositórios públicos [Dev Center do Mercado Livre].

---

## 🧑‍💻 Autor
*   **Guilherme Caliari Louzado Oliveira**
*   *Estudante de Ciência da Computação - 2º Período*


