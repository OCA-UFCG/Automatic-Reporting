import { BrandMark } from './BrandMark.jsx'
import { IndicatorScores } from './IndicatorScores.jsx'
import { MacrothemeSummary } from './MacrothemeSummary.jsx'
import { MetricCards } from './MetricCards.jsx'
import { RadarSection } from './RadarSection.jsx'

export function ReportCover({ cover }) {
  if (!cover) {
    return null
  }

  return (
    <section className="report-cover">
      <div className="cover-header">
        <div className="cover-meta">
          <BrandMark />
          <span className="cover-date">{cover.data_extenso}</span>
        </div>
      </div>

      <div className="cover-content">
        <div className="cover-kicker">Relatorio geral</div>
        <h1 className="cover-city">
          {cover.cidade_nome}
          {cover.uf ? ` (${cover.uf})` : ''}
        </h1>

        <MetricCards metrics={cover.metricas} />
        <RadarSection score={cover.score} />
        <MacrothemeSummary macrotheme={cover.macrotema} />
        <IndicatorScores indicators={cover.macrotema?.indicadores} />
      </div>
    </section>
  )
}
