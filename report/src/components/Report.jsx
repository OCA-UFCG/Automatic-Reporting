import React from 'react';
import { pdfStyles } from '../styles.js';
import Cover from './Cover.jsx';
import ThemeDetail from './ThemeDetail.jsx';
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
        <PdfPageHeader />
        <Cover cover={cover} />
        <ThemeDetail macrotema={cover.macrotema} />
        {dados.map((_, idx) => (
          <div key={idx} className="doc-content" dangerouslySetInnerHTML={{ __html: docsHtml }} />
        ))}
        <PdfFooter />
      </body>
    </html>
  );
}
