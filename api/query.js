// Serverless proxy for the Wiwynn Cerberus sn_info API.
//
// The upstream endpoint is reachable from the public internet but sends no
// CORS headers, so a browser cannot call it directly from another origin.
// This function performs the call server-side, where CORS does not apply.

const API_URL_TEMPLATE = 'https://apim.wiwynn.com/nifi/{env}/api/cerberus/v1/sn_info';

const ALLOWED_ENVS = ['prd', 'dev'];
const UPSTREAM_TIMEOUT_MS = 55000;

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed. Use POST.' });
  }

  const body = typeof req.body === 'string' ? safeParse(req.body) : req.body;
  if (!body) {
    return res.status(400).json({ error: 'Request body must be valid JSON.' });
  }

  const env = String(body.env || 'prd').toLowerCase();
  // Strict allow-list: `env` is interpolated into the upstream URL path.
  if (!ALLOWED_ENVS.includes(env)) {
    return res.status(400).json({ error: `Unknown env "${env}". Expected one of: ${ALLOWED_ENVS.join(', ')}.` });
  }

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
    const elapsedMs = Date.now() - startedAt;

    if (!upstream.ok) {
      return res.status(502).json({
        error: `Upstream returned HTTP ${upstream.status}.`,
        upstreamStatus: upstream.status,
        upstreamBody: text.slice(0, 2000),
        elapsedMs,
      });
    }

    // The upstream answers 200 with a completely empty body when nothing
    // matches, so treat that as "no rows" rather than as a parse failure.
    if (!text.trim()) {
      return res.status(200).json({ records: [], elapsedMs, empty: true });
    }

    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      return res.status(502).json({
        error: 'Upstream returned a 200 response that is not valid JSON.',
        upstreamBody: text.slice(0, 2000),
        elapsedMs,
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
      elapsedMs,
      empty: records.length === 0,
      truncated: hitCap !== undefined,
      cap: hitCap,
    });
  } catch (err) {
    const elapsedMs = Date.now() - startedAt;
    if (err.name === 'AbortError') {
      return res.status(504).json({ error: `Upstream did not respond within ${UPSTREAM_TIMEOUT_MS / 1000}s.`, elapsedMs });
    }
    return res.status(502).json({ error: `Could not reach the upstream API: ${err.message}`, elapsedMs });
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
