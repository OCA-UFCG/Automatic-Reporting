import React from 'react';
import { CoverBrand } from './Brand.jsx';

export default function ThemeDetail({ macrotema }) {
  const items = macrotema.descricao_html || macrotema.descricao_paragrafos;
  if (!items || items.length === 0) return null;

  return (
    <section className="theme-detail-page">
      <div className="theme-detail-header">
        <CoverBrand />
      </div>
      <h2 className="theme-detail-title">Detalhamento do tema</h2>
      {items.map((item, idx) => {
        if (typeof item === 'string' && item.startsWith('<figure')) {
          return null;
        }
        if (macrotema.descricao_html) {
          return <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />;
        }
        return <p key={idx} className="theme-detail-text">{item}</p>;
      })}
    </section>
  );
}
