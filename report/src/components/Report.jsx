import React from 'react';
import { pdfStyles } from '../styles.js';
import Cover from './cover/Cover.jsx';
import { PdfPageHeader, PdfFooter } from './PdfLayout.jsx';

export default function Report({ cover, docsHtml, dados }) {
  return (
    <html lang="pt-BR">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Data Nordeste – Relatório modelo</title>
        <style dangerouslySetInnerHTML={{ __html: pdfStyles }} />
      </head>
      <body>
        <PdfPageHeader data={cover.data_extenso} />
        <PdfFooter />
        <Cover cover={cover} />
        {dados.map((_, idx) => (
          <div key={idx} className="doc-content" dangerouslySetInnerHTML={{ __html: docsHtml }} />
        ))}
      </body>
    </html>
  );
}
