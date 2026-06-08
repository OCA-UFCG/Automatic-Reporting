import React from 'react';

export default function ScoreLegend() {
  return (
    <div className="score-legend">
      <p className="score-legend-title">Legenda</p>
      <div className="score-legend-bar" aria-label="Legenda do score">
        <div className="score-legend-item score-legend-very-high">Muito acima da média</div>
        <div className="score-legend-item score-legend-high">Acima da média</div>
        <div className="score-legend-item score-legend-low">Abaixo da média</div>
        <div className="score-legend-item score-legend-very-low">Muito abaixo da média</div>
      </div>
    </div>
  );
}
