import React from 'react';
import { CoverBrand } from './Brand.jsx';

export default function ThemeDetail({ macrotema }) {
  if (!macrotema.descricao_paragrafos || macrotema.descricao_paragrafos.length === 0) return null;

  return (
    <section className="theme-detail-page">
      <p className="theme-detail-kicker">Relatório V1</p>
      <div className="theme-detail-header">
        <CoverBrand />
      </div>
      <h2 className="theme-detail-title">Detalhamento do tema</h2>
      {macrotema.descricao_paragrafos.map((paragrafo, idx) => (
        <p key={idx} className="theme-detail-text">{paragrafo}</p>
      ))}
    </section>
  );
}
