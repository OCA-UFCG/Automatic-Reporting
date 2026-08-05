import React from 'react';
import { pdfStyles } from '../styles.js';
import Cover from './cover/Cover.jsx';
import { PdfFooter } from './PdfLayout.jsx';

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
        <PdfPageHeader />
        <PdfFooter data={cover.data_extenso} />
        <Cover cover={cover} />
        <div className="doc-content" dangerouslySetInnerHTML={{ __html: docsHtml }} />
      </body>
    </html>
  );
}
