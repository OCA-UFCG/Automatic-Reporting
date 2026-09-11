import React from 'react';

export default function ThemeDetail({ macrotema }) {
  const items = macrotema.descricao_html || macrotema.descricao_paragrafos;
  if (!items || items.length === 0) return null;

  return (
    <section className="theme-detail-section">
      <div className="cover-relatorio-geral-wrap theme-detail-content">
        {items.map((item, idx) => {
          if (typeof item === 'string' && item.startsWith('<figure')) {
            return null;
          }
          if (macrotema.descricao_html) {
            return <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />;
          }
          return <p key={idx} className="theme-detail-text">{item}</p>;
        })}
      </div>
    </section>
  );
}
