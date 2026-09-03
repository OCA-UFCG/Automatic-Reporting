import React from 'react';
import IndicatorScoreCard from './IndicatorScoreCard.jsx';

const INDICADORES_POR_LINHA = 3;

function agruparEmLinhas(indicadores, tamanho) {
  const linhas = [];
  for (let i = 0; i < indicadores.length; i += tamanho) {
    linhas.push(indicadores.slice(i, i + tamanho));
  }
  return linhas;
}

export default function IndicatorScores({ macrotema }) {
  if (!macrotema.indicadores || macrotema.indicadores.length === 0) return null;
  const linhas = agruparEmLinhas(macrotema.indicadores, INDICADORES_POR_LINHA);
  return (
    <div className="indicator-scores">
      <h2 className="cover-kicker">Panorama de indicadores</h2>
      <div className="indicator-score-grid">
        {linhas.map((linha, idx) => (
          <div className="indicator-score-row" key={idx}>
            {linha.map((indicador, idxIndicador) => (
              <IndicatorScoreCard key={idxIndicador} indicador={indicador} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
