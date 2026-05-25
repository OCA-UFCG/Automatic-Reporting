export function IndicatorScores({ indicators = [] }) {
  if (!indicators.length) {
    return null
  }

  return (
    <section className="indicator-scores">
      <h2 className="indicator-scores-title">Scores por indicador</h2>
      <div className="indicator-score-grid">
        {indicators.map((indicator) => (
          <article className="indicator-score-card" key={indicator.nome}>
            <span className="indicator-icon" aria-hidden="true" />
            <div>
              <div className="indicator-name">{indicator.nome}</div>
              <div className="indicator-source">{indicator.fonte}</div>
            </div>
            <span className={`indicator-badge indicator-badge-${indicator.classe}`}>
              {indicator.score}
            </span>
          </article>
        ))}
      </div>
    </section>
  )
}
