import React from 'react';
import { IndicatorIcon } from '../Brand.jsx';

export default function IndicatorScoreCard({ indicador }) {
  return (
    <div className="indicator-score-card">
      <IndicatorIcon icone={indicador.icone} />
      <div>
        <div className="indicator-name">{indicador.nome}</div>
        <div className="indicator-source">{indicador.fonte}</div>
      </div>
      <span className={`indicator-badge indicator-badge-${indicador.classe}`}>{indicador.score}</span>
    </div>
  );
}
