import React from 'react';

export default function MacrothemeSummary({ macrotema }) {
  return (
    <div className="macrotheme-summary">
      <h2 className="macrotheme-summary-title">Resumo do relatório</h2>
      <p className="macrotheme-summary-text">{macrotema.resumo}</p>
    </div>
  );
}
