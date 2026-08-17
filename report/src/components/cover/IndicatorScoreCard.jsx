import React from 'react';
import { IndicatorIcon } from '../Brand.jsx';

const BADGE_COLORS = {
  'very-high': '#758F21',
  'high':      '#F99C07',
  'low':       '#BF1621',
  'very-low':  '#BF1621',
  'unknown':   '#9A9DA5',
};

export default function IndicatorScoreCard({ indicador }) {
  const badgeColor = BADGE_COLORS[indicador.classe] || '#9A9DA5';

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
        <span
          className="indicator-badge"
          style={{ background: badgeColor }}
        >
          {indicador.score}
        </span>
      </div>

      <div className="indicator-score-card-footer">
        Score com base na Meta nacional
      </div>
    </div>
  );
}
