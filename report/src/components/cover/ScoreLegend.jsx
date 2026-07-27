import React from 'react';

export default function ScoreLegend() {
  return (
    <div className="score-legend">
      <p className="score-legend-title">Legenda</p>
      <div className="score-legend-bar" aria-label="Legenda do score">
        <div className="score-legend-item" style={{ background: '#BF1621', color: '#F8F7F8' }}>Abaixo</div>
        <div className="score-legend-item" style={{ background: '#F99C07', color: '#292829' }}>Na média</div>
        <div className="score-legend-item" style={{ background: '#758F21', color: '#F8F7F8' }}>Acima</div>
      </div>
      <p className="score-legend-footnote">Com base na meta</p>
    </div>
  );
}
