import React from 'react';

export default function ScoreCard({ score }) {
  return (
    <div className="score-card">
      <div className="score-header">
        <div className="score-title">Média do município</div>
      </div>
      <div className="score-body">
        <div className="score-line">
          <div className="score-value">{score.valor}<span className="score-max">/{score.maximo}</span></div>
        </div>
        {score.descricao ? <p className="score-description">{score.descricao}</p> : null}
      </div>
    </div>
  );
}
