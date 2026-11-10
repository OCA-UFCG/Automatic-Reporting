import React from 'react';
import { pdfStyles } from '../styles.js';
import Cover from './cover/Cover.jsx';
import ContinueComDataNordeste from './ContinueComDataNordeste.jsx';
import { PdfPageHeader, PdfFooter } from './PdfLayout.jsx';
import { rotuloDaUnidade } from './rotuloDaUnidade.js';

export default function Report({ cover, docsHtml }) {
  return (
    <html lang="pt-BR">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Data Nordeste – Relatório modelo</title>
        <style dangerouslySetInnerHTML={{ __html: pdfStyles }} />
      </head>
      <body>
        <PdfPageHeader label={rotuloDaUnidade(cover)} />
        <Cover cover={cover} />
        <div className="doc-content" dangerouslySetInnerHTML={{ __html: docsHtml }} />
        <ContinueComDataNordeste />
        <PdfFooter data={cover.data_extenso} />
      </body>
    </html>
  );
}
