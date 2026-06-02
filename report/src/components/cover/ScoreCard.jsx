import React from 'react';
import { ScoreIcon } from '../Brand.jsx';

export default function ScoreCard({ score }) {
  return (
    <div className="score-card">
      <div className="score-header">
        <ScoreIcon />
        <div className="score-title">Score geral em relação ao Brasil</div>
      </div>
      <div className="score-body">
        <div className="score-line">
          <div className="score-value">{score.valor}<span className="score-max">/{score.maximo}</span></div>
          <div className="score-status">{score.status}</div>
        </div>
        <p className="score-description">{score.descricao}</p>
      </div>
    </div>
  );
}
