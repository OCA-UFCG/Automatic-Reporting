import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import Report from './components/Report.jsx';

const input = process.argv[2];
if (!input) {
  process.stderr.write('Usage: node ssr-entry.jsx <JSON props>\n');
  process.exit(1);
}

let props;
try {
  props = JSON.parse(input);
} catch (e) {
  process.stderr.write(`Invalid JSON: ${e.message}\n`);
  process.exit(1);
}

const html = '<!DOCTYPE html>\n' + renderToStaticMarkup(React.createElement(Report, props));
process.stdout.write(html);
