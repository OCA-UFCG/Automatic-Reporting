import React from 'react';
import { CoverBrand, PdfCoverBrand } from '../Brand.jsx';
import MetricCard from './MetricCard.jsx';
import ScoreLegend from './ScoreLegend.jsx';
import MacrothemeCard from './MacrothemeCard.jsx';
import MacrothemeSummary from './MacrothemeSummary.jsx';
import IndicatorScores from './IndicatorScores.jsx';
import ThemeDetail from '../ThemeDetail.jsx';

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
        {cover.resumo_relatorio_html?.length > 0 && (
          <div className="cover-resumo-relatorio-wrap">
            {cover.resumo_relatorio_html.map((item, idx) => (
              <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />
            ))}
          </div>
        )}
        <h1 className="cover-city">
          {cover.cidade_nome}{cover.uf ? ` (${cover.uf})` : null}
        </h1>
        {cover.resumo_cidade_html?.length > 0 && (
          <div className="cover-resumo-cidade-wrap">
            {cover.resumo_cidade_html.map((item, idx) => (
              <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />
            ))}
          </div>
        )}
        <div className="cover-kicker">Características Gerais</div>
          <div className="cover-metrics">
            {cover.metricas.map((m, idx) => (
              <MetricCard key={idx} metrica={m} />
            ))}
        </div>
        <div className="cover-maps-group">
          {cover.mapa_principal && (
            <div className="cover-mapa-principal" dangerouslySetInnerHTML={{ __html: cover.mapa_principal }} />
          )}
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
        </div>
        <MacrothemeSummary macrotema={cover.macrotema} />
        <MacrothemeCard macrotema={cover.macrotema} />
        <IndicatorScores macrotema={cover.macrotema} />
        <ScoreLegend />
        <ThemeDetail macrotema={cover.macrotema} />

      </div>
    </section>
  );
}
