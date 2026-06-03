import React from 'react';
import { CoverBrand, PdfCoverBrand } from '../Brand.jsx';
import MetricCard from './MetricCard.jsx';
import ScoreLegend from './ScoreLegend.jsx';
import MacrothemeCard from './MacrothemeCard.jsx';
import MacrothemeSummary from './MacrothemeSummary.jsx';
import IndicatorScores from './IndicatorScores.jsx';

export default function Cover({ cover }) {
  const hasMaps = cover.macrotema?.descricao_html?.length > 0;

  return (
    <section className="report-cover">
      <div className="cover-header">
        <div className="cover-meta">
          <CoverBrand />
          <PdfCoverBrand />
          <span className="cover-date">{cover.data_extenso}</span>
        </div>
      </div>
      <div className="cover-content">
        <div className="cover-kicker">Relatório geral</div>
        <h1 className="cover-city">
          {cover.cidade_nome}{cover.uf ? ` (${cover.uf})` : null}
        </h1>
        <div className="cover-metrics">
          {cover.metricas.map((m, idx) => (
            <MetricCard key={idx} metrica={m} />
          ))}
        </div>
        {hasMaps && (
          <div className="cover-maps">
            {cover.macrotema.descricao_html
              .filter(item => typeof item === 'string' && item.startsWith('<figure'))
              .slice(0, 2)
              .map((item, idx) => (
                <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />
              ))}
          </div>
        )}
        <MacrothemeCard macrotema={cover.macrotema} />
        <MacrothemeSummary macrotema={cover.macrotema} />
        <IndicatorScores macrotema={cover.macrotema} />
        <ScoreLegend />
      </div>
    </section>
  );
}
