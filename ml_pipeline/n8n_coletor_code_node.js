// ============================================================================
// COLETOR n8n — node "Code" (JavaScript), modo "Run Once for All Items"
// ============================================================================
// Substitui toda a bagunça de HTTP Request nodes por UMA coleta limpa.
// Pré-requisito: um node OAuth a montante (o seu "HTTP Request1" com
// grant_type=refresh_token) que produza access_token e user_id.
//
// Usa this.helpers.httpRequest (caminho que NÃO tem o bug PolicyAgent 403 —
// ver memória do projeto). fetch/require NÃO funcionam no sandbox do Code node.
//
// Saída: 1 item com { generated_at, seller_id, items: [...] }.
// Ligue este node num "Write Binary File" / "Move Binary Data" ou copie o JSON
// do output e salve como ml_pipeline/dados_conta.json para o analista.py ler.
// ============================================================================

const accessToken = $('HTTP Request1').item.json.access_token;
const sellerId    = $('HTTP Request1').item.json.user_id;

const H = { 'Authorization': `Bearer ${accessToken}`, 'Accept': 'application/json' };
const helpers = this.helpers;
const get = (url) => helpers.httpRequest({ method: 'GET', url, headers: H, json: true });

// 1) Todos os IDs de anúncio do vendedor (paginado, 50 por página)
let itemIds = [];
let offset = 0;
while (true) {
  const page = await get(
    `https://api.mercadolibre.com/users/${sellerId}/items/search?limit=50&offset=${offset}`
  );
  itemIds = itemIds.concat(page.results || []);
  const total = (page.paging && page.paging.total) || itemIds.length;
  if (!page.results || page.results.length < 50 || offset + 50 >= total) break;
  offset += 50;
}

// Diagnóstico: erros aparecem na saída em vez de sumirem em silêncio.
// detalharErro extrai o CORPO da resposta do ML (onde vem o motivo real), não só o status.
const erros = [];
function detalharErro(e) {
  const partes = [];
  if (e && e.message) partes.push(e.message);
  const corpo = (e && (e.response?.body ?? e.response?.data ?? e.error ?? e.cause?.response?.body));
  if (corpo) {
    try { partes.push('corpo: ' + (typeof corpo === 'string' ? corpo : JSON.stringify(corpo)).slice(0, 400)); }
    catch (_) { /* ignora */ }
  }
  return partes.join(' | ') || String(e);
}

// 2) Perguntas: UMA chamada paginada no endpoint do vendedor, agrupando por item
//    (melhor que 1 chamada por anúncio, e é o endpoint certo p/ quem vende)
const perguntasPorItem = {};
try {
  let qOffset = 0;
  while (true) {
    const q = await get(
      `https://api.mercadolibre.com/my/received_questions/search?limit=50&offset=${qOffset}&api_version=4`
    );
    const lote = q.questions || [];
    for (const x of lote) {
      const iid = x.item_id;
      if (!perguntasPorItem[iid]) perguntasPorItem[iid] = [];
      perguntasPorItem[iid].push({
        pergunta: x.text,
        resposta: x.answer ? x.answer.text : null,
      });
    }
    const total = (q.total !== undefined) ? q.total : lote.length;
    if (lote.length < 50 || qOffset + 50 >= total) break;
    qOffset += 50;
  }
} catch (e) {
  erros.push('perguntas via /my/received_questions/search: ' + detalharErro(e));
  // fallback: tenta por item, uma vez, só p/ descobrir se o outro endpoint funciona
  try {
    const primeiro = itemIds[0];
    const q2 = await get(`https://api.mercadolibre.com/questions/search?item=${primeiro}&api_version=4`);
    erros.push('fallback /questions/search?item= retornou ' + ((q2.questions || []).length) + ' perguntas');
  } catch (e2) {
    erros.push('fallback /questions/search?item= também falhou: ' + detalharErro(e2));
  }
}

// 3) Para cada item: detalhes + descrição (+ perguntas já agrupadas)
const out = [];
for (const id of itemIds) {
  const item = await get(`https://api.mercadolibre.com/items/${id}`);

  let description = '';
  try {
    const d = await get(`https://api.mercadolibre.com/items/${id}/description`);
    description = (d && (d.plain_text || d.text)) || '';
  } catch (e) {
    erros.push(`descrição ${id}: ` + (e.message || String(e)));
  }

  const questions = perguntasPorItem[id] || [];

  out.push({
    id: item.id,
    title: item.title,
    price: item.price,
    original_price: item.original_price,
    listing_type_id: item.listing_type_id,      // gold_pro=Premium, gold_special=Clássico
    status: item.status,
    available_quantity: item.available_quantity,
    sold_quantity: item.sold_quantity,           // NÃO usar para conversão (é acumulado)
    catalog_listing: item.catalog_listing,
    catalog_product_id: item.catalog_product_id,
    video_id: item.video_id || null,             // clip publicado? (sem isso o analista acha que não tem)
    condition: item.condition,
    category_id: item.category_id,
    shipping: item.shipping,                      // logistic_type (fulfillment=Full, etc.), free_shipping
    pictures: (item.pictures || []).map(p => p.secure_url),   // TODAS as imagens
    attributes: (item.attributes || []).map(a => ({ nome: a.name, valor: a.value_name })),
    variations: (item.variations || []).map(v => ({
      id: v.id,
      price: v.price,
      available_quantity: v.available_quantity,
      atributos: (v.attribute_combinations || []).map(a => ({ nome: a.name, valor: a.value_name })),
    })),
    description,
    questions,
  });
}

return [{
  json: {
    generated_at: new Date().toISOString(),
    seller_id: sellerId,
    total_perguntas: Object.values(perguntasPorItem).reduce((s, v) => s + v.length, 0),
    _erros: erros,          // se vier vazio, tudo certo; se vier algo, é o diagnóstico
    items: out,
  },
}];
