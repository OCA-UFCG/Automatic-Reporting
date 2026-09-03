import React from 'react';
import { MacrothemeIcon } from '../Brand.jsx';

export default function MacrothemeCard({ macrotema }) {
  const cardStyle = macrotema?.cor
    ? { '--macrotheme-color': macrotema.cor }
    : undefined;
  const score = macrotema.score;
  return (
    <div className="macrotheme-card" style={cardStyle}>
      <div className="macrotheme-card-left">
        <span className="macrotheme-icon-box" aria-hidden="true">
          <MacrothemeIcon icone={macrotema.icone} color={macrotema.cor} />
        </span>
        <span className="macrotheme-name">{macrotema.nome}</span>
      </div>
      {score?.valor && (
        <div className="macrotheme-card-right">
          <span className="macrotheme-score-label">Média do tema</span>
          <span className="macrotheme-score-value">
            {score.valor}
            {score.maximo && <span className="macrotheme-score-max">/{score.maximo}</span>}
          </span>
        </div>
      )}
    </div>
  );
}
