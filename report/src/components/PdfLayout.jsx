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

export function PdfFooter() {
  return (
    <footer className="pdf-footer">
      <span className="pdf-footer-label">Relatório automático do Data Nordeste</span>
      <span className="pdf-footer-page" aria-label="Número da página" />
    </footer>
  );
}
