import React from 'react';
import { MetricIcon } from '../Brand.jsx';

export default function MetricCard({ metrica }) {
  return (
    <div className="metric-card">
      <div className="metric-heading">
        <span className="metric-icon-box">
          <MetricIcon />
        </span>
        <div className="metric-text">
          <div className="metric-label">{metrica.rotulo}</div>
          <div className="metric-source">{metrica.fonte}</div>
        </div>
      </div>
      <div className="metric-content">
        <div className="metric-value">
          {metrica.valor}{metrica.sufixo ? <span className="metric-unit"> {metrica.sufixo}</span> : null}
        </div>
        <div className="metric-caption">{metrica.caption}</div>
      </div>
    </div>
  );
}