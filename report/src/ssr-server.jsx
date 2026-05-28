import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'http';
import Report from './components/Report.jsx';

const PORT = parseInt(process.env.SSR_PORT || '3001', 10);

const server = createServer(async (req, res) => {
  if (req.method !== 'POST' || req.url !== '/render') {
    res.writeHead(405).end('Method Not Allowed');
    return;
  }

  let body = '';
  for await (const chunk of req) body += chunk;

  try {
    const props = JSON.parse(body);
    const html = '<!DOCTYPE html>\n' + renderToStaticMarkup(React.createElement(Report, props));

    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  } catch (err) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    res.end(`Invalid request: ${err.message}`);
  }
});

server.listen(PORT, () => {
  process.stderr.write(`SSR server listening on port ${PORT}\n`);
});

process.on('SIGTERM', () => server.close(() => process.exit(0)));
process.on('SIGINT', () => server.close(() => process.exit(0)));
