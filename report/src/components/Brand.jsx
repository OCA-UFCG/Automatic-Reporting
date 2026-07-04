import React from 'react';

export function BrandSquares() {
  return (
    <span className="brand-squares" aria-hidden="true">
      <span /><span /><span /><span /><span /><span />
    </span>
  );
}

export function CoverBrand() {
  return (
    <div className="cover-brand" aria-label="Data Nordeste">
      <div className="brand-mark">
        <BrandSquares />
        <span>NE</span>
      </div>
      <span className="brand-subtitle">Data Nordeste</span>
    </div>
  );
}

export function PdfPageHeaderBrand() {
  return (
    <div className="pdf-page-header-brand" aria-label="Data Nordeste">
      <svg className="pdf-page-header-logo" viewBox="0 0 150 58" role="img" aria-label="Data Nordeste">
        <rect x="0" y="0" width="150" height="58" fill="none" />
        <rect x="7" y="14" width="6" height="6" fill="#ef7d00" />
        <rect x="17" y="14" width="6" height="6" fill="#0a8f43" />
        <rect x="27" y="14" width="6" height="6" fill="#204f9e" />
        <rect x="7" y="24" width="6" height="6" fill="#204f9e" />
        <rect x="17" y="24" width="6" height="6" fill="#ef7d00" />
        <rect x="27" y="24" width="6" height="6" fill="#0a8f43" />
        <text x="39" y="31" fill="#008d43" fontFamily="Arial, sans-serif" fontSize="31" fontWeight="900">NE</text>
        <text x="7" y="48" fill="#222" fontFamily="Arial, sans-serif" fontSize="6" fontWeight="700">DATA NORDESTE</text>
      </svg>
    </div>
  );
}

export function PdfCoverBrand() {
  return (
    <div className="pdf-cover-brand" aria-label="Data Nordeste">
      <svg viewBox="0 0 130 44" role="img" aria-label="Data Nordeste">
        <rect x="0" y="0" width="130" height="44" fill="none" />
        <rect x="2" y="6" width="7" height="7" fill="#BCD441" rx="1" />
        <rect x="11" y="6" width="7" height="7" fill="#009046" rx="1" />
        <rect x="20" y="6" width="7" height="7" fill="#D6528E" rx="1" />
        <rect x="2" y="15" width="7" height="7" fill="#35B9CF" rx="1" />
        <rect x="11" y="15" width="7" height="7" fill="#211F5F" rx="1" />
        <rect x="20" y="15" width="7" height="7" fill="#CA962B" rx="1" />
        <rect x="2" y="24" width="7" height="7" fill="#EF424C" rx="1" />
        <rect x="11" y="24" width="7" height="7" fill="#F99A3A" rx="1" />
        <rect x="20" y="24" width="7" height="7" fill="#FDDA57" rx="1" />
        <text x="32" y="22" fill="#009046" fontFamily="Arial, sans-serif" fontSize="20" fontWeight="900">DNE</text>
        <text x="2" y="38" fill="#514C50" fontFamily="Arial, sans-serif" fontSize="5" fontWeight="700" letterSpacing="0.5">DATA NORDESTE</text>
      </svg>
    </div>
  );
}

export function MetricIcon() {
  return (
    <svg className="metric-icon" viewBox="0 0 24 24" aria-hidden="true" color="#018f39">
      <path d="M4 17h16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M7 15l3.1-4.2 2.7 2.8 3.3-5.1L20 15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="10.1" cy="10.8" r="1.1" fill="currentColor" />
      <circle cx="12.8" cy="13.6" r="1.1" fill="currentColor" />
      <circle cx="16.1" cy="8.5" r="1.1" fill="currentColor" />
    </svg>
  );
}

export function ScoreIcon() {
  return (
    <svg className="score-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 16l5-5 4 4 6-7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M15 8h4v4" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const MACROTHEME_ICONS = {
  health: <path d="M10 5h4v5h5v4h-5v5h-4v-5H5v-4h5z" fill="currentColor" />,
  book: <path d="M5 5.5c2.6 0 4.5.5 7 2v11c-2.5-1.5-4.4-2-7-2zM19 5.5c-2.6 0-4.5.5-7 2v11c2.5-1.5 4.4-2 7-2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />,
  people: <path d="M8.5 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM15.5 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM3.5 19c.7-3.2 2.5-5 5-5s4.3 1.8 5 5zM12.5 19c.5-2.2 1.7-3.7 3.6-3.7 2 0 3.4 1.4 4 3.7z" fill="currentColor" />,
  drop: <path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />,
  water: <path d="M3 9c2 0 2 1.5 4 1.5S9 9 11 9s2 1.5 4 1.5S17 9 21 9M3 15c2 0 2 1.5 4 1.5S9 15 11 15s2 1.5 4 1.5S17 15 21 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />,
};

export function MacrothemeIcon({ icone }) {
  return (
    <svg className="macrotheme-icon" viewBox="0 0 24 24" color="#ff3045">
      {MACROTHEME_ICONS[icone] || (
        <path d="M4 17h16M7 15l3-4 3 3 4-6 3 7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

const INDICATOR_ICONS = {
  hospital: <path d="M4 21V8h5V3h6v5h5v13H4zM10 7h4M12 10v7M8.5 13.5h7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
  vaccine: <path d="M7 5l12 12M14 4l6 6M4 14l6 6M9 7l8 8-5 5-8-8z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
  birth: <><circle cx="12" cy="8" r="3" fill="none" stroke="currentColor" strokeWidth="2" /><path d="M7 21c.6-4 2.3-6 5-6s4.4 2 5 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></>,
  shield: <path d="M12 3l7 3v5c0 4.5-2.7 8-7 10-4.3-2-7-5.5-7-10V6z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />,
  book: <path d="M5 5.5c2.6 0 4.5.5 7 2v11c-2.5-1.5-4.4-2-7-2zM19 5.5c-2.6 0-4.5.5-7 2v11c2.5-1.5 4.4-2 7-2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />,
  people: <path d="M8.5 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM15.5 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM3.5 19c.7-3.2 2.5-5 5-5s4.3 1.8 5 5zM12.5 19c.5-2.2 1.7-3.7 3.6-3.7 2 0 3.4 1.4 4 3.7z" fill="currentColor" />,
  drop: <path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />,
  water: <path d="M3 9c2 0 2 1.5 4 1.5S9 9 11 9s2 1.5 4 1.5S17 9 21 9M3 15c2 0 2 1.5 4 1.5S9 15 11 15s2 1.5 4 1.5S17 15 21 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />,
};

export function IndicatorIcon({ icone }) {
  return (
    <svg className="indicator-icon" viewBox="0 0 24 24" aria-hidden="true" color="#ff3045">
      {INDICATOR_ICONS[icone] || (
        <path d="M4 17h16M7 15l3-4 3 3 4-6 3 7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}
