import { ChartsSection } from './components/ChartsSection.jsx'
import { Footer } from './components/Footer.jsx'
import { PdfHeader } from './components/PdfHeader.jsx'
import { ReportCover } from './components/ReportCover.jsx'
import { TextContent } from './components/TextContent.jsx'
import { ThemeDetail } from './components/ThemeDetail.jsx'

export function ReportDocument({
  cover,
  charts = [],
  docsHtml = '',
  reportCss = '',
}) {
  return (
    <html lang="pt-BR">
      <head>
        <meta charSet="utf-8" />
        <title>Relatorio automatico</title>
        <style>{reportCss}</style>
      </head>
      <body>
        <PdfHeader />
        <ReportCover cover={cover} />
        <ThemeDetail macrotheme={cover?.macrotema} />
        <ChartsSection charts={charts} />
        <TextContent html={docsHtml} />
        <Footer />
      </body>
    </html>
  )
}
