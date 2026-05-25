import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ReportDocument } from './index.js'

export function renderReportHtml(input) {
  const html = renderToStaticMarkup(
    <ReportDocument
      cover={input.cover}
      charts={input.charts ?? input.graficos ?? []}
      docsHtml={input.docsHtml ?? input.docs_html ?? ''}
      reportCss={input.reportCss ?? ''}
    />,
  )

  return `<!doctype html>${html}`
}
