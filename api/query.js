// Serverless proxy for the Wiwynn Cerberus sn_info API.
//
// The upstream endpoint is reachable from the public internet but sends no
// CORS headers, so a browser cannot call it directly from another origin.
// This function performs the call server-side, where CORS does not apply.
//
// Two modes:
//   guided — the query form builds SITE / TYPE / SN and the proxy decides
//            the query parameters.
//   raw    — the manual tab supplies the request body and query parameters
//            verbatim, for experimenting against the API.
//
// Both modes are locked to POST /sn_info. The spec's other three endpoints
// (hwkey_info, gpkey_info, hwkey_action) are PUTs that write to the
// production database, and this tool is deliberately read-only.

const API_URL_TEMPLATE = 'https://apim.wiwynn.com/nifi/{env}/api/cerberus/v1/sn_info';

const ALLOWED_ENVS = ['prd', 'dev'];
const UPSTREAM_TIMEOUT_MS = 55000;
const MAX_RAW_BODY_CHARS = 1000000;
const MAX_RAW_PARAMS = 20;

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed. Use POST.' });
  }

  const body = typeof req.body === 'string' ? safeParse(req.body) : req.body;
  if (!body || typeof body !== 'object') {
    return res.status(400).json({ error: 'Request body must be valid JSON.' });
  }

  const env = String(body.env || 'prd').toLowerCase();
  // Strict allow-list: `env` is interpolated into the upstream URL path.
  if (!ALLOWED_ENVS.includes(env)) {
    return res.status(400).json({ error: `Unknown env "${env}". Expected one of: ${ALLOWED_ENVS.join(', ')}.` });
  }

  return body.mode === 'raw' ? handleRaw(res, env, body) : handleGuided(res, env, body);
}

/* ---------- guided mode ---------- */

async function handleGuided(res, env, body) {
  // Per the API spec, TYPE is the only required field: omitting SITE means
  // "no site restriction", which is a documented, supported query mode.
  const type = typeof body.type === 'string' ? body.type.trim() : '';
  if (!type) {
    return res.status(400).json({ error: '"type" is required.' });
  }
  const site = typeof body.site === 'string' ? body.site.trim() : '';

  const snList = Array.isArray(body.sn)
    ? body.sn.map((s) => String(s).trim()).filter(Boolean)
    : [];

  // The upstream rejects JSON null for every field, so omit keys instead.
  const payload = { TYPE: type };
  if (site) payload.SITE = site;
  if (snList.length) payload.SN = snList;

  if (body.rowLimit !== undefined && body.rowLimit !== null && body.rowLimit !== '') {
    const rowLimit = Number(body.rowLimit);
    if (!Number.isInteger(rowLimit) || rowLimit < 1) {
      return res.status(400).json({ error: '"rowLimit" must be a positive integer.' });
    }
    payload.ROW_LIMIT = rowLimit;
  }

  const url = new URL(API_URL_TEMPLATE.replace('{env}', env));

  // Without these params the upstream returns only records whose download
  // status is still empty — the pending queue. With them, every record is
  // eligible. Sending them only alongside an SN list keeps the old Streamlit
  // behaviour: "look up these serials" vs "show me what is still pending".
  const usedAllParams = snList.length > 0;
  if (usedAllParams) {
    url.searchParams.set('HwkeyDownloadStatus', 'all');
    url.searchParams.set('GPkeyDownloadStatus', 'all');
  }

  // The proxy decides things the form cannot see — whether the status
  // parameters were added, which keys were dropped — so report the request
  // that actually went upstream. The manual tab replays it verbatim, and it
  // is what gets handed to IT when something needs explaining.
  const request = {
    url: url.toString(),
    body: payload,
    params: [...url.searchParams].map(([key, value]) => ({ key, value })),
  };

  const call = await callUpstream(url, payload);

  if (call.error) {
    return res.status(call.status).json({ error: call.error, elapsedMs: call.elapsedMs, request });
  }

  if (!call.ok) {
    return res.status(502).json({
      error: `Upstream returned HTTP ${call.status}.`,
      upstreamStatus: call.status,
      upstreamBody: call.text.slice(0, 2000),
      elapsedMs: call.elapsedMs,
      request,
    });
  }

  // The upstream answers 200 with a completely empty body when nothing
  // matches, so treat that as "no rows" rather than as a parse failure.
  if (!call.text.trim()) {
    return res.status(200).json({ records: [], elapsedMs: call.elapsedMs, empty: true, truncated: false, request });
  }

  let parsed;
  try {
    parsed = JSON.parse(call.text);
  } catch {
    return res.status(502).json({
      error: 'Upstream returned a 200 response that is not valid JSON.',
      upstreamBody: call.text.slice(0, 2000),
      elapsedMs: call.elapsedMs,
      request,
    });
  }

  // Normalise to an array so the client never has to guess the shape.
  const records = Array.isArray(parsed) ? parsed : [parsed];

  // Nothing in the response says whether rows were dropped, so landing
  // exactly on a known cap is the only available signal. Both caps are
  // checked rather than letting ROW_LIMIT shadow the 1000 one: as of
  // 2026-09-16 PRD still ignores ROW_LIMIT (spec v4.3.0 is not deployed),
  // so assuming it applies would mask a real 1000-record truncation.
  const caps = [];
  if (usedAllParams) caps.push(1000);
  if (payload.ROW_LIMIT) caps.push(payload.ROW_LIMIT);
  const hitCap = caps.find((c) => records.length === c);

  return res.status(200).json({
    records,
    elapsedMs: call.elapsedMs,
    empty: records.length === 0,
    truncated: hitCap !== undefined,
    cap: hitCap,
    request,
  });
}

/* ---------- raw mode ---------- */

async function handleRaw(res, env, body) {
  if (body.payload === undefined || body.payload === null || typeof body.payload !== 'object') {
    return res.status(400).json({ error: 'Raw mode needs a "payload" object.' });
  }

  let payloadText;
  try {
    payloadText = JSON.stringify(body.payload);
  } catch {
    return res.status(400).json({ error: 'The payload could not be serialised to JSON.' });
  }
  if (payloadText.length > MAX_RAW_BODY_CHARS) {
    return res.status(400).json({ error: `Payload is too large (${payloadText.length} chars, limit ${MAX_RAW_BODY_CHARS}).` });
  }

  const url = new URL(API_URL_TEMPLATE.replace('{env}', env));
  const params = Array.isArray(body.params) ? body.params : [];
  if (params.length > MAX_RAW_PARAMS) {
    return res.status(400).json({ error: `Too many query parameters (limit ${MAX_RAW_PARAMS}).` });
  }
  for (const p of params) {
    if (!p || typeof p.key !== 'string' || !p.key.trim()) continue;
    url.searchParams.append(p.key.trim(), p.value === undefined || p.value === null ? '' : String(p.value));
  }

  const call = await callUpstream(url, body.payload);

  if (call.error) {
    return res.status(call.status).json({ error: call.error, elapsedMs: call.elapsedMs, url: url.toString() });
  }

  // Raw mode reports exactly what came back, including non-200 responses and
  // empty bodies, so the caller can see the real behaviour rather than a
  // normalised view of it.
  let records = null;
  if (call.text.trim()) {
    try {
      const parsed = JSON.parse(call.text);
      if (Array.isArray(parsed)) records = parsed;
    } catch { /* not JSON — the caller sees the raw text */ }
  }

  return res.status(200).json({
    url: url.toString(),
    status: call.status,
    ok: call.ok,
    elapsedMs: call.elapsedMs,
    byteLength: Buffer.byteLength(call.text, 'utf8'),
    bodyText: call.text,
    records,
    requestBody: payloadText,
  });
}

/* ---------- shared ---------- */

async function callUpstream(url, payload) {
  const startedAt = Date.now();
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), UPSTREAM_TIMEOUT_MS);

  try {
    const upstream = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      signal: abort.signal,
    });
    const text = await upstream.text();
    return { ok: upstream.ok, status: upstream.status, text, elapsedMs: Date.now() - startedAt };
  } catch (err) {
    const elapsedMs = Date.now() - startedAt;
    if (err.name === 'AbortError') {
      return { error: `Upstream did not respond within ${UPSTREAM_TIMEOUT_MS / 1000}s.`, status: 504, elapsedMs };
    }
    return { error: `Could not reach the upstream API: ${err.message}`, status: 502, elapsedMs };
  } finally {
    clearTimeout(timer);
  }
}

function safeParse(s) {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}
