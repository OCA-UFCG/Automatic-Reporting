import React from 'react';
import { IndicatorIcon } from '../Brand.jsx';

export default function IndicatorScoreCard({ indicador, cor }) {
  return (
    <div className="indicator-score-card">
      <div className="indicator-score-card-inner">
        <div className="indicator-score-card-header">
          <div className="indicator-score-card-info-row">
            <span className="indicator-icon-box">
              <IndicatorIcon icone={indicador.icone} cor={cor} />
            </span>
            <div className="indicator-text">
              <div className="indicator-name">{indicador.nome}</div>
              <div className="indicator-source">{indicador.fonte}</div>
            </div>
          </div>
          <div className="indicator-value">
            {indicador.valor}
          </div>
        </div>

        {/* Sempre renderizado, mesmo vazio: o rodapé tem altura fixa e é o
            que iguala os cabeçalhos — sem ele volta a faixa branca quando o
            vizinho é mais alto (ex. educação, sem unidade no banco). */}
        <div className="indicator-score-card-footer">
          <div className="indicator-score-card-footer-text">
            {indicador.rodape || "\u00A0"}
          </div>
        </div>
      </div>
    </div>
  );
}
