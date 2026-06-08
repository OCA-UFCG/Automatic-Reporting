import React from 'react';

export default function ScoreLegend() {
  return (
    <div className="score-legend">
      <p className="score-legend-title">Legenda</p>
      <div className="score-legend-bar" aria-label="Legenda do score">
        <div className="score-legend-item score-legend-low">Abaixo</div>
        <div className="score-legend-item score-legend-medium">Na média</div>
        <div className="score-legend-item score-legend-high">Acima</div>
      </div>
      <p className="score-legend-footnote">Com base na meta</p>
    </div>
  );
}
