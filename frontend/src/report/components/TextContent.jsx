export function TextContent({ html }) {
  if (!html) {
    return null
  }

  return (
    <main
      className="report-doc-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
