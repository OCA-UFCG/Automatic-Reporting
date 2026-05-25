export function MetricCards({ metrics = [] }) {
  if (!metrics.length) {
    return null
  }

  return (
    <div className="cover-metrics">
      {metrics.map((metric) => (
        <article className="metric-card" key={`${metric.rotulo}-${metric.valor}`}>
          <div className="metric-heading">
            <div>
              <div className="metric-label">{metric.rotulo}</div>
              <div className="metric-source">{metric.fonte}</div>
            </div>
          </div>
          <div className="metric-value">
            {metric.valor}
            {metric.sufixo ? <span className="metric-unit"> {metric.sufixo}</span> : null}
          </div>
          <div className="metric-caption">{metric.caption}</div>
        </article>
      ))}
    </div>
  )
}
