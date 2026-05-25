export function RadarSection({ score }) {
  if (!score) {
    return null
  }

  return (
    <section className="region-radar-section">
      <h2 className="region-radar-title">Radar da regiao</h2>
      <div className="region-radar-row">
        <div className="region-radar-card" aria-label="Radar da regiao">
          {/* TODO: migrar o SVG do radar para um componente proprio. */}
        </div>
        <div className="score-column">
          <div className="score-card">
            <div className="score-header">
              <div className="score-title">Score geral em relacao ao Brasil</div>
            </div>
            <div className="score-body">
              <div className="score-line">
                <div className="score-value">
                  {score.valor}
                  <span className="score-max">/{score.maximo}</span>
                </div>
                <div className="score-status">{score.status}</div>
              </div>
              <p className="score-description">{score.descricao}</p>
            </div>
          </div>
          <p className="score-support-text">{score.texto_apoio}</p>
        </div>
      </div>
    </section>
  )
}
