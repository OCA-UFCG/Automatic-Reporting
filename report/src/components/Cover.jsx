import React from 'react';
import { CoverBrand, MetricIcon, ScoreIcon, MacrothemeIcon, IndicatorIcon } from './Brand.jsx';

function MetricCard({ metrica }) {
  return (
    <div className="metric-card">
      <div className="metric-heading">
        <MetricIcon />
        <div>
          <div className="metric-label">{metrica.rotulo}</div>
          <div className="metric-source">{metrica.fonte}</div>
        </div>
      </div>
      <div className="metric-value">
        {metrica.valor}{metrica.sufixo ? <span className="metric-unit"> {metrica.sufixo}</span> : null}
      </div>
      <div className="metric-caption">{metrica.caption}</div>
    </div>
  );
}

function RadarChart() {
  return (
    <div className="region-radar-card" aria-label="Radar da região">
      <svg className="region-radar-chart" viewBox="0 0 360 260" role="img" aria-label="Gráfico radar da região">
        <g transform="translate(180 132)">
          <polygon className="radar-grid" points="0,-82 71,-41 71,41 0,82 -71,41 -71,-41" />
          <polygon className="radar-grid" points="0,-65.6 56.8,-32.8 56.8,32.8 0,65.6 -56.8,32.8 -56.8,-32.8" />
          <polygon className="radar-grid" points="0,-49.2 42.6,-24.6 42.6,24.6 0,49.2 -42.6,24.6 -42.6,-24.6" />
          <polygon className="radar-grid" points="0,-32.8 28.4,-16.4 28.4,16.4 0,32.8 -28.4,16.4 -28.4,-16.4" />
          <polygon className="radar-grid" points="0,-16.4 14.2,-8.2 14.2,8.2 0,16.4 -14.2,8.2 -14.2,-8.2" />
          <line className="radar-axis" x1="0" y1="0" x2="0" y2="-82" />
          <line className="radar-axis" x1="0" y1="0" x2="71" y2="-41" />
          <line className="radar-axis" x1="0" y1="0" x2="71" y2="41" />
          <line className="radar-axis" x1="0" y1="0" x2="0" y2="82" />
          <line className="radar-axis" x1="0" y1="0" x2="-71" y2="41" />
          <line className="radar-axis" x1="0" y1="0" x2="-71" y2="-41" />
          <polygon className="radar-area" points="0,-49.2 42.6,-24.6 28.4,16.4 0,65.6 -42.6,24.6 -28.4,-16.4" />
          <text className="radar-tick" x="4" y="-65">4</text>
          <text className="radar-tick" x="4" y="-49">3</text>
          <text className="radar-tick" x="4" y="-33">2</text>
          <text className="radar-tick" x="4" y="-17">1</text>
          <text className="radar-label" x="0" y="-99" textAnchor="middle">Saúde</text>
          <text className="radar-label" x="94" y="-48" textAnchor="start">Educação</text>
          <text className="radar-label" x="92" y="38" textAnchor="start">Desenvolvimento Social</text>
          <text className="radar-label" x="48" y="97" textAnchor="start">Economia e Renda</text>
          <text className="radar-label" x="0" y="112" textAnchor="middle">Demografia</text>
          <text className="radar-label" x="-92" y="75" textAnchor="middle">Infraestrutura e Saneamento</text>
          <text className="radar-label" x="-105" y="20" textAnchor="end">Meio Ambiente</text>
          <text className="radar-label" x="-88" y="-47" textAnchor="end">Segurança Hídrica</text>
        </g>
      </svg>
    </div>
  );
}

function ScoreCard({ score }) {
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

function ScoreLegend() {
  return (
    <div className="score-legend">
      <p className="score-legend-title">Legenda</p>
      <div className="score-legend-bar" aria-label="Legenda do score">
        <div className="score-legend-item score-legend-very-high">Muito acima da média</div>
        <div className="score-legend-item score-legend-high">Acima da média</div>
        <div className="score-legend-item score-legend-low">Abaixo da média</div>
        <div className="score-legend-item score-legend-very-low">Muito abaixo da média</div>
      </div>
    </div>
  );
}

function MacrothemeCard({ macrotema }) {
  return (
    <div className="macrotheme-card">
      <div className="macrotheme-title">
        <span className="macrotheme-icon-box" aria-hidden="true">
          <MacrothemeIcon icone={macrotema.icone} />
        </span>
        <span className="macrotheme-name">{macrotema.nome}</span>
      </div>
      <span className="macrotheme-status">{macrotema.status}</span>
    </div>
  );
}

function MacrothemeSummary({ macrotema }) {
  return (
    <div className="macrotheme-summary">
      <h2 className="macrotheme-summary-title">Resumo</h2>
      <p className="macrotheme-summary-text">{macrotema.resumo}</p>
    </div>
  );
}

function IndicatorScoreCard({ indicador }) {
  return (
    <div className="indicator-score-card">
      <IndicatorIcon icone={indicador.icone} />
      <div>
        <div className="indicator-name">{indicador.nome}</div>
        <div className="indicator-source">{indicador.fonte}</div>
      </div>
      <span className={`indicator-badge indicator-badge-${indicador.classe}`}>{indicador.score}</span>
    </div>
  );
}

function IndicatorScores({ macrotema }) {
  if (!macrotema.indicadores || macrotema.indicadores.length === 0) return null;
  return (
    <div className="indicator-scores">
      <h2 className="indicator-scores-title">Scores por indicador</h2>
      <div className="indicator-score-grid">
        {macrotema.indicadores.map((indicador, idx) => (
          <IndicatorScoreCard key={idx} indicador={indicador} />
        ))}
      </div>
    </div>
  );
}

export default function Cover({ cover }) {
  return (
    <section className="report-cover">
      <div className="cover-header">
        <div className="cover-meta">
          <CoverBrand />
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
        <h2 className="region-radar-title">Radar da região</h2>
        <div className="region-radar-row">
          <RadarChart />
          <div className="score-column">
            <ScoreCard score={cover.score} />
            <p className="score-support-text">{cover.score.texto_apoio}</p>
          </div>
        </div>
        <ScoreLegend />
        <MacrothemeCard macrotema={cover.macrotema} />
        <MacrothemeSummary macrotema={cover.macrotema} />
        <IndicatorScores macrotema={cover.macrotema} />
      </div>
    </section>
  );
}
