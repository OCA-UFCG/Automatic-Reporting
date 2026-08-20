import React from 'react';
import { CoverBrand, PdfCoverBrand } from '../Brand.jsx';
import IndicatorScores from './IndicatorScores.jsx';
import MacrothemeCard from './MacrothemeCard.jsx';
import MetricCard from './MetricCard.jsx';
import ScoreLegend from './ScoreLegend.jsx';
import ThemeDetail from '../ThemeDetail.jsx';

const LIGHT_BADGE_COLORS = new Set(['#FFD65A', '#B0CC41']);

export default function Cover({ cover }) {
  const hasMaps = cover.macrotema?.descricao_html?.length > 0;
  const macrotemas = cover.macrotemas && cover.macrotemas.length > 0
    ? cover.macrotemas
    : (cover.macrotema ? [cover.macrotema] : []);
  const macrotemasTags = cover.macrotemas_tags && cover.macrotemas_tags.length > 0
    ? cover.macrotemas_tags
    : macrotemas;
  const cidade = [cover.cidade_nome, cover.uf].filter(Boolean).join(' - ');

  return (
    <>
    <section className="report-cover">
      <div className="cover-header">
        <div className="cover-meta">
          <CoverBrand />
          <PdfCoverBrand />
          <span className="cover-start-label">Dados municipais reunidos em uma única plataforma</span>
        </div>
      </div>
      <header className="cover-report-header">
        <p className="cover-report-eyebrow">Relatório</p>
        <h1 className="cover-report-title">{cidade || 'Município'}</h1>
        {macrotemasTags.length > 0 && (
          <div className="cover-macrotheme-tags" aria-label="Macrotemas selecionados">
            {macrotemasTags.map((macrotema, idx) => (
              <span
                className="cover-macrotheme-tag"
                style={{
                  backgroundColor: macrotema.cor || '#018F39',
                  color: LIGHT_BADGE_COLORS.has(macrotema.cor) ? '#292829' : '#FFFFFF',
                }}
                key={macrotema.slug || `${macrotema.nome}-${idx}`}
              >
                {macrotema.nome}
              </span>
            ))}
          </div>
        )}
      </header>

      <div className="cover-content">
        {cover.relatorio_geral_html?.length > 0 && (
          <section className="cover-presentation">
            <div className="cover-kicker">Apresentação</div>
            <div className="cover-relatorio-geral-wrap">
              {cover.relatorio_geral_html.map((item, idx) => (
                <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />
              ))}
            </div>
          </section>
        )}

        <div className="cover-kicker">Características Gerais</div>

        {cover.resumo_cidade_html?.length > 0 && (
          <div className="cover-resumo-cidade-wrap">
            {cover.resumo_cidade_html.map((item, idx) => (
              <div key={idx} dangerouslySetInnerHTML={{ __html: item }} />
            ))}
          </div>
        )}

        <div className="cover-metrics">
          {cover.metricas.slice(0, 2).map((m, idx) => (
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

      </div>
    </section>

    {macrotemas.map((macrotema, idx) => (
      <section className="theme-detail-page" key={idx}>
        <div className="theme-detail-top">
          <MacrothemeCard macrotema={macrotema} />

          <IndicatorScores macrotema={macrotema} />

          <ScoreLegend />
        </div>

        <ThemeDetail macrotema={macrotema} />
      </section>
    ))}
    </>
  );
}
