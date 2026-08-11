"""
Autenticacao ML sem n8n.

Le o refresh_token de tokens.json (ou, na primeira vez, do node HTTP Request1
do workflow n8n "coletor ml"), troca por um access_token e GRAVA O NOVO
refresh_token imediatamente — o ML rotaciona o refresh a cada uso e perder
o novo significa refazer o OAuth do zero.
"""
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
TOKENS = os.path.join(AQUI, "tokens.json")
N8N_DB = os.path.expanduser("~/atendimento-ia/n8n/database.sqlite")
WORKFLOW_ID = "QYtG4K59YiK1FJjT"


def _do_n8n():
    """Semente: puxa client_id/secret/refresh_token do node HTTP Request1."""
    con = sqlite3.connect(f"file:{N8N_DB}?mode=ro", uri=True)
    (nodes,) = con.execute(
        "SELECT nodes FROM workflow_entity WHERE id=?", (WORKFLOW_ID,)
    ).fetchone()
    con.close()
    for node in json.loads(nodes):
        if node.get("name") == "HTTP Request1":
            params = node["parameters"]["bodyParameters"]["parameters"]
            return {p["name"]: p["value"] for p in params}
    raise RuntimeError("node HTTP Request1 nao encontrado no workflow")


def carregar():
    if os.path.exists(TOKENS):
        with open(TOKENS) as fh:
            return json.load(fh)
    creds = _do_n8n()
    return {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
    }


def salvar(dados):
    tmp = TOKENS + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(dados, fh, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKENS)


def access_token():
    """Devolve (access_token, seller_id), persistindo o refresh rotacionado."""
    dados = carregar()
    corpo = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": dados["client_id"],
            "client_secret": dados["client_secret"],
            "refresh_token": dados["refresh_token"],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.mercadolibre.com/oauth/token",
        data=corpo,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        novo = json.loads(resp.read())

    # grava ANTES de qualquer outra coisa poder falhar
    dados["refresh_token"] = novo["refresh_token"]
    dados["access_token"] = novo["access_token"]
    dados["user_id"] = novo["user_id"]
    salvar(dados)
    return novo["access_token"], novo["user_id"]


if __name__ == "__main__":
    try:
        tok, seller = access_token()
    except urllib.error.HTTPError as e:
        print("FALHA no refresh:", e.code, e.read().decode()[:300], file=sys.stderr)
        sys.exit(1)
    print(f"OK  seller_id={seller}  access_token={tok[:10]}...({len(tok)} chars)")
    print(f"novo refresh_token salvo em {TOKENS}")
