// Local dev server: a minimal stand-in for Vercel's Node serverless runtime.
//
// Serves index.html and routes POST /api/query through the real handler in
// api/query.js, so the whole path can be exercised without installing or
// logging into the Vercel CLI.
//
//   node scripts/dev-server.mjs   ->  http://localhost:3000
//
// This file is a development aid only; Vercel never runs it.

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = Number(process.env.PORT) || 3000;

const handler = (await import(pathToFileURL(path.join(ROOT, 'api', 'query.js')).href)).default;

// Vercel hands the function an Express-like `res`; Node's own response object
// has none of these, so wrap it with just the parts api/query.js uses.
function wrapResponse(res) {
  const api = {
    statusCode: 200,
    setHeader: (key, value) => res.setHeader(key, value),
    status(code) {
      api.statusCode = code;
      return api;
    },
    json(body) {
      res.writeHead(api.statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(body));
      return api;
    },
  };
  return api;
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString('utf8');
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return raw; // api/query.js re-parses strings and reports the error itself
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (url.pathname === '/api/query') {
    req.body = await readBody(req);
    try {
      await handler(req, wrapResponse(res));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: `Handler threw: ${err.message}` }));
    }
    return;
  }

  if (url.pathname === '/' || url.pathname === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(fs.readFileSync(path.join(ROOT, 'index.html')));
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log(`dev server running at http://localhost:${PORT}`);
  console.log('press Ctrl+C to stop');
});
