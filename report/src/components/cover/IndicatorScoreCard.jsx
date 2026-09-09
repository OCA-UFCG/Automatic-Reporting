import React from 'react';
import { IndicatorIcon } from '../Brand.jsx';

export default function IndicatorScoreCard({ indicador }) {
  return (
    <div className="indicator-score-card">
      <div className="indicator-score-card-header">
        <div className="indicator-score-card-info-row">
          <span className="indicator-icon-box">
            <IndicatorIcon icone={indicador.icone} />
          </span>
          <div className="indicator-text">
            <div className="indicator-name">{indicador.nome}</div>
            <div className="indicator-source">{indicador.fonte}</div>
          </div>
        </div>
        <div className="indicator-value">
          {indicador.score}
        </div>
      </div>

      <div className="indicator-score-card-footer">
        Score com base na Meta nacional
      </div>
    </div>
  );
}
