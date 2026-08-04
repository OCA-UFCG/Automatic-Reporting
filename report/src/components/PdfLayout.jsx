import React from 'react';
import { PdfPageHeaderBrand } from './Brand.jsx';

export function PdfPageHeader({ data }) {
  return (
    <div className="pdf-page-header">
      <PdfPageHeaderBrand />
      {data && <span className="cover-date">{data}</span>}
    </div>
  );
}

export function PdfFooter({ data }) {
  return (
    <footer className="pdf-footer">
      <span className="pdf-footer-generation">
        {data ? `Relatório gerado em ${data}` : 'Relatório automático do Data Nordeste'}
      </span>
      <span className="pdf-footer-page" aria-hidden="true" />
    </footer>
  );
}
