import React from 'react';
import IndicatorScoreCard from './IndicatorScoreCard.jsx';

export default function IndicatorScores({ macrotema }) {
  if (!macrotema.indicadores || macrotema.indicadores.length === 0) return null;
  return (
    <div className="indicator-scores">
      <h2 className="indicator-scores-title">Scores por indicador</h2>
      <div className="indicator-score-grid">
        {macrotema.indicadores.map((indicador, idx) => (
          <IndicatorScoreCard key={idx} indicador={indicador} />
        ))}
      </div>
    </div>
  );
}
