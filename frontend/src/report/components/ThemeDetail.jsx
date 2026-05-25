export function ThemeDetail({ macrotheme }) {
  const paragraphs = macrotheme?.descricao_paragrafos ?? []

  if (!paragraphs.length) {
    return null
  }

  return (
    <section className="theme-detail-header">
      <h2>{macrotheme.nome}</h2>
      {paragraphs.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
    </section>
  )
}
