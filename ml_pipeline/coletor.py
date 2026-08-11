"""
Coletor ML — substitui o Code node do n8n, rodando nativo no Mac (IPv6, sem
o bug PolicyAgent que bloqueava o node HTTP do n8n).

Alem do que o coletor antigo pegava (ficha/fotos/atributos/descricao), busca
o que faltava e que e o ponto da analise de midia:
  - PEDIDOS reais da janela (/orders/search) -> vendas, unidades, receita
  - VISITAS por anuncio na mesma janela      -> conversao com numerador e
                                                denominador da MESMA janela
                                                (o bug historico do pipeline)

Saida: dados_conta.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import ml_auth

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "dados_conta.json")
DIAS = int(os.environ.get("DIAS", "30"))

erros = []


def get(url, token, tentativas=3):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    for n in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            corpo = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503) and n < tentativas - 1:
                time.sleep(2 ** n)
                continue
            raise RuntimeError(f"HTTP {e.code} em {url.split('?')[0]}: {corpo}")
        except Exception as e:
            if n < tentativas - 1:
                time.sleep(2 ** n)
                continue
            raise RuntimeError(f"{type(e).__name__} em {url.split('?')[0]}: {e}")


def paginar(url_base, token, chave, limite=50, teto=2000):
    """Percorre endpoints paginados do ML (results/questions/orders)."""
    fora, offset = [], 0
    while offset < teto:
        sep = "&" if "?" in url_base else "?"
        pagina = get(f"{url_base}{sep}limit={limite}&offset={offset}", token)
        lote = pagina.get(chave) or []
        fora.extend(lote)
        total = (pagina.get("paging") or {}).get("total", pagina.get("total", len(fora)))
        if len(lote) < limite or offset + limite >= total:
            break
        offset += limite
    return fora


def main():
    token, seller = ml_auth.access_token()
    ate = datetime.now(timezone.utc)
    desde = ate - timedelta(days=DIAS)
    fmt = "%Y-%m-%dT%H:%M:%S.000-00:00"
    print(f"seller {seller} | janela {DIAS}d ({desde:%d/%m} a {ate:%d/%m})", flush=True)

    # ---------------------------------------------------------------- anuncios
    ids = paginar(
        f"https://api.mercadolibre.com/users/{seller}/items/search", token, "results"
    )
    print(f"anuncios: {len(ids)}", flush=True)

    # ---------------------------------------------------------------- pedidos
    pedidos, por_item = [], defaultdict(
        lambda: {"pedidos": 0, "unidades": 0, "receita": 0.0}
    )
    try:
        crus = paginar(
            "https://api.mercadolibre.com/orders/search"
            f"?seller={seller}"
            f"&order.date_created.from={urllib.parse.quote(desde.strftime(fmt))}"
            f"&order.date_created.to={urllib.parse.quote(ate.strftime(fmt))}"
            "&sort=date_desc",
            token,
            "results",
        )
        for o in crus:
            itens = []
            for oi in o.get("order_items") or []:
                it = oi.get("item") or {}
                iid = it.get("id")
                qtd = oi.get("quantity") or 0
                preco = oi.get("unit_price") or 0.0
                itens.append(
                    {
                        "item_id": iid,
                        "titulo": it.get("title"),
                        "variacao": it.get("variation_id"),
                        "quantidade": qtd,
                        "preco_unitario": preco,
                    }
                )
                if o.get("status") != "cancelled":
                    por_item[iid]["pedidos"] += 1
                    por_item[iid]["unidades"] += qtd
                    por_item[iid]["receita"] += qtd * preco
            pedidos.append(
                {
                    "id": o.get("id"),
                    "data": o.get("date_created"),
                    "status": o.get("status"),
                    "total": o.get("total_amount"),
                    "pago": o.get("paid_amount"),
                    "itens": itens,
                }
            )
        print(f"pedidos na janela: {len(pedidos)}", flush=True)
    except Exception as e:
        erros.append(f"pedidos: {e}")
        print(f"!! pedidos falharam: {e}", flush=True)

    # ---------------------------------------------------------------- visitas
    # /items/visits (multiget) recusa data com hora; time_window por item e o
    # caminho estavel — mesma janela dos pedidos, que e o que importa.
    visitas = {}
    for iid in ids:
        try:
            d = get(
                f"https://api.mercadolibre.com/items/{iid}/visits/time_window"
                f"?last={DIAS}&unit=day",
                token,
            )
            visitas[iid] = d.get("total_visits", 0)
        except Exception as e:
            erros.append(f"visitas {iid}: {e}")
    print(
        f"visitas coletadas: {len(visitas)}/{len(ids)} anuncios "
        f"({sum(visitas.values())} visitas)",
        flush=True,
    )

    # ---------------------------------------------------------------- detalhes
    saida = []
    for n, iid in enumerate(ids, 1):
        try:
            item = get(f"https://api.mercadolibre.com/items/{iid}", token)
        except Exception as e:
            erros.append(f"item {iid}: {e}")
            continue
        try:
            d = get(f"https://api.mercadolibre.com/items/{iid}/description", token)
            desc = d.get("plain_text") or d.get("text") or ""
        except Exception:
            desc = ""

        v = por_item.get(iid, {"pedidos": 0, "unidades": 0, "receita": 0.0})
        vis = visitas.get(iid, 0)
        saida.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "price": item.get("price"),
                "original_price": item.get("original_price"),
                "listing_type_id": item.get("listing_type_id"),
                "status": item.get("status"),
                "sub_status": item.get("sub_status"),
                "available_quantity": item.get("available_quantity"),
                "sold_quantity": item.get("sold_quantity"),
                "catalog_listing": item.get("catalog_listing"),
                "catalog_product_id": item.get("catalog_product_id"),
                "video_id": item.get("video_id"),
                "health": item.get("health"),
                "condition": item.get("condition"),
                "category_id": item.get("category_id"),
                "permalink": item.get("permalink"),
                "shipping": item.get("shipping"),
                "pictures": [p.get("secure_url") for p in item.get("pictures") or []],
                "attributes": [
                    {"nome": a.get("name"), "valor": a.get("value_name")}
                    for a in item.get("attributes") or []
                ],
                "variations": [
                    {
                        "id": x.get("id"),
                        "price": x.get("price"),
                        "available_quantity": x.get("available_quantity"),
                        "sold_quantity": x.get("sold_quantity"),
                        "atributos": [
                            {"nome": a.get("name"), "valor": a.get("value_name")}
                            for a in x.get("attribute_combinations") or []
                        ],
                    }
                    for x in item.get("variations") or []
                ],
                "description": desc,
                # --- metricas da MESMA janela (a correcao do bug historico) ---
                "janela_dias": DIAS,
                "visitas_janela": vis,
                "pedidos_janela": v["pedidos"],
                "unidades_janela": v["unidades"],
                "receita_janela": round(v["receita"], 2),
                "conversao_janela": (
                    round(100 * v["pedidos"] / vis, 2) if vis else None
                ),
            }
        )
        if n % 10 == 0:
            print(f"  {n}/{len(ids)} detalhes", flush=True)

    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seller_id": seller,
        "janela": {"dias": DIAS, "de": desde.isoformat(), "ate": ate.isoformat()},
        "resumo": {
            "anuncios": len(saida),
            "pedidos": len(pedidos),
            "unidades": sum(x["unidades_janela"] for x in saida),
            "receita": round(sum(x["receita_janela"] for x in saida), 2),
            "visitas": sum(x["visitas_janela"] for x in saida),
        },
        "_erros": erros,
        "pedidos": pedidos,
        "items": saida,
    }
    with open(SAIDA, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"\n-> {SAIDA}")
    print(json.dumps(doc["resumo"], indent=2))
    if erros:
        print(f"\n{len(erros)} erro(s):")
        for e in erros[:10]:
            print("  -", e)


if __name__ == "__main__":
    sys.exit(main())
