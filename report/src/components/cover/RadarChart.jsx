import React from 'react';

export default function RadarChart() {
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
