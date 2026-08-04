import React from 'react';
import { CoverBrand, PdfCoverBrand } from '../Brand.jsx';
import IndicatorScores from './IndicatorScores.jsx';
import MacrothemeCard from './MacrothemeCard.jsx';
import MetricCard from './MetricCard.jsx';
import RadarChart from './RadarChart.jsx';
import ScoreCard from './ScoreCard.jsx';
import ScoreLegend from './ScoreLegend.jsx';
import ThemeDetail from '../ThemeDetail.jsx';

export default function Cover({ cover }) {
  const hasMaps = cover.macrotema?.descricao_html?.length > 0;
  const macrotemas = cover.macrotemas && cover.macrotemas.length > 0
    ? cover.macrotemas
    : (cover.macrotema ? [cover.macrotema] : []);

  return (
    <>
    <section className="report-cover">
      <div className="cover-header">
        <div className="cover-meta">
          <CoverBrand />
          <PdfCoverBrand />
        </div>
      </div>
      <div className="cover-content">

        <div className="cover-kicker">Relatório geral</div>
        {cover.relatorio_geral_html?.length > 0 && (
          <div className="cover-relatorio-geral-wrap">
            {cover.relatorio_geral_html.map((item, idx) => (
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

        <div className="cover-metrics">
          {cover.metricas.map((m, idx) => (
            <MetricCard key={idx} metrica={m} />
          ))}
        </div>

        <section className="diagnostic-block">
          <div className="cover-kicker">Diagnóstico do município</div>
          <div className="diagnostic-grid">
            <div className="radar-card">
              <RadarChart />
            </div>
            <div className="score-diagnostic-card">
              <ScoreCard score={cover.score} />
              {cover.diagnostico_cidade_html?.length > 0 ? (
                cover.diagnostico_cidade_html.map((item, idx) => (
                  <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />
                ))
              ) : (
                <p className="score-diagnostic-text">
                  {cover.score?.texto_apoio || cover.macrotema?.resumo || ''}
                </p>
              )}
            </div>
          </div>
        </section>

      </div>
    </section>

    <section className="resumo-relatorio-page">
      <h2 className="cover-kicker">Resumo do relatório</h2>
      {cover.resumo_relatorio_html?.length > 0 ? (
        cover.resumo_relatorio_html.map((item, i) => (
          <div key={i} dangerouslySetInnerHTML={{ __html: item }} />
        ))
      ) : (
        cover.resumo_relatorio ? (
          <p className="theme-detail-text">{cover.resumo_relatorio}</p>
        ) : null
      )}
    </section>

    {macrotemas.map((macrotema, idx) => (
      <React.Fragment key={idx}>
        <MacrothemeCard macrotema={macrotema} />

        <IndicatorScores macrotema={macrotema} />

        <ScoreLegend />

        <ThemeDetail macrotema={macrotema} />
      </React.Fragment>
    ))}
    </>
  );
}
