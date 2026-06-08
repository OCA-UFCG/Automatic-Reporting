import React from 'react';
import { PdfPageHeaderBrand } from './Brand.jsx';

export function PdfPageHeader() {
  return (
    <div className="pdf-page-header">
      <PdfPageHeaderBrand />
    </div>
  );
}

export function PdfFooter() {
  return (
    <footer className="pdf-footer">
      <span>Relatório automático do Data Nordeste</span>
      <span className="pdf-footer-page" aria-label="Número da página" />
    </footer>
  );
}
