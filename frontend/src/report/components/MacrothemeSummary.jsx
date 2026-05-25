export function MacrothemeSummary({ macrotheme }) {
  if (!macrotheme) {
    return null
  }

  return (
    <>
      <section className="macrotheme-card">
        <div className="macrotheme-title">
          <span className="macrotheme-icon-box" aria-hidden="true" />
          <span className="macrotheme-name">{macrotheme.nome}</span>
        </div>
        <span className="macrotheme-status">{macrotheme.status}</span>
      </section>
      <section className="macrotheme-summary">
        <h2 className="macrotheme-summary-title">Resumo</h2>
        <p className="macrotheme-summary-text">{macrotheme.resumo}</p>
      </section>
    </>
  )
}
