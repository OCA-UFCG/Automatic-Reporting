import React from 'react';

const ARTIGO_DO = new Set(['Saneamento', 'Hidráulica']);

function diagnosticarNome(nome) {
  const artigo = ARTIGO_DO.has(nome) ? 'do' : 'da';
  return `Diagnóstico ${artigo} ${nome}`;
}

export default function ThemeDetail({ macrotema }) {
  const items = macrotema.descricao_html || macrotema.descricao_paragrafos;
  if (!items || items.length === 0) return null;

  return (
    <section className="theme-detail-section">
      <h2 className="theme-detail-heading">{diagnosticarNome(macrotema.nome)}</h2>
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
