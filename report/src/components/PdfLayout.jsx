import React from 'react';
import { PdfPageHeaderBrand } from './Brand.jsx';

export function PdfPageHeader() {
  return (
    <div className="pdf-page-header">
      <PdfPageHeaderBrand />
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
