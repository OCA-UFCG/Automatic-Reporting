export function ChartsSection({ charts = [] }) {
  if (!charts.length) {
    return null
  }

  return (
    <section className="report-charts">
      {charts.map((chart) => (
        <figure className="report-chart" key={chart}>
          <img src={chart} alt="" />
        </figure>
      ))}
    </section>
  )
}
