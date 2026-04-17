import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const MACROTEMAS = [
  'Ver todos',
  'Demografia',
  'Educação',
  'Economia e Renda',
  'Saúde',
  'Infraestrutura e Saneamento',
  'Segurança Hídrica',
  'Meio Ambiente',
  'Publicações',
  'Catálogo de Dados',
  'Plataformas conectadas'
]

function App() {
  const [cities, setCities] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [selectedMacrotema, setSelectedMacrotema] = useState(MACROTEMAS[0])
  const [selectedCity, setSelectedCity] = useState('')
  const [citySearch, setCitySearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function fetchCities() {
      try {
        setLoading(true)
        const response = await fetch(`${API_BASE}/cities`)
        if (!response.ok) {
          throw new Error('Falha ao carregar cidades')
        }
        const data = await response.json()
        setCities(Array.isArray(data) ? data : [])
      } catch (err) {
        setError(err.message || 'Erro ao carregar cidades')
      } finally {
        setLoading(false)
      }
    }

    fetchCities()
  }, [])

  const cityCount = useMemo(() => cities.length, [cities])
  const filteredCities = useMemo(() => {
    const term = citySearch.trim().toLowerCase()
    if (!term) return cities
    return cities.filter((city) => city.toLowerCase().includes(term))
  }, [cities, citySearch])

  function openReport() {
    if (!selectedCity) {
      return
    }

    const url = `${API_BASE}/relatorio/${encodeURIComponent(selectedCity)}`
    window.open(url, '_blank')
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <span className="eyebrow">Sudene • Gerador de relatórios</span>
          <h1>Geração de relatório para Sudene</h1>
          <p className="subtitle">
            Escolha um macrotema e uma cidade para montar o relatório. Por enquanto, a API recebe apenas a cidade.
          </p>

          <div className="hero-actions">
            <button
              type="button"
              className="report-button"
              onClick={() => setShowForm(true)}
              disabled={loading || Boolean(error)}
            >
              Gerar relatório
            </button>
            <div className="stat-pill">{cityCount} cidades disponíveis</div>
          </div>
        </div>

        <aside className="hero-card">
          <p className="hero-card-label">Macrotemas disponíveis</p>
          <div className="macrotema-tags">
            {MACROTEMAS.slice(1).map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        </aside>
      </section>

      {loading && <p className="status-text">Carregando cidades...</p>}
      {error && <p className="error">{error}</p>}

      {showForm && !loading && !error && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)} role="presentation">
          <section className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Formulário de relatório</h2>
                <p>Selecione o macrotema e a cidade desejada.</p>
              </div>
              <button type="button" className="close-button" onClick={() => setShowForm(false)}>
                ×
              </button>
            </div>

            <div className="form-grid">
              <div>
                <label className="label" htmlFor="macrotema">
                  Macrotema
                </label>
                <select
                  id="macrotema"
                  className="select"
                  value={selectedMacrotema}
                  onChange={(event) => setSelectedMacrotema(event.target.value)}
                >
                  {MACROTEMAS.map((macrotema) => (
                    <option key={macrotema} value={macrotema}>
                      {macrotema}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label" htmlFor="cidadeSearch">
                  Buscar cidade
                </label>
                <input
                  id="cidadeSearch"
                  className="select"
                  type="text"
                  placeholder="Digite para filtrar cidades..."
                  value={citySearch}
                  onChange={(event) => setCitySearch(event.target.value)}
                />
              </div>
            </div>

            <div className="list-header">
              <span>Lista de cidades</span>
              <span>{filteredCities.length} encontradas</span>
            </div>

            <div className="city-grid">
              {filteredCities.map((city) => (
                <button
                  key={city}
                  type="button"
                  className={`city-card ${selectedCity === city ? 'city-card--active' : ''}`}
                  onClick={() => setSelectedCity(city)}
                >
                  {city}
                </button>
              ))}
            </div>

            <div className="selection-summary">
              <div>
                <span className="summary-label">Macrotema</span>
                <strong>{selectedMacrotema}</strong>
              </div>
              <div>
                <span className="summary-label">Cidade</span>
                <strong>{selectedCity || 'Nenhuma selecionada'}</strong>
              </div>
            </div>

            <div className="actions">
              <button type="button" className="report-button" onClick={openReport} disabled={!selectedCity}>
                Gerar relatório
              </button>
              <button type="button" className="secondary-button" onClick={() => setShowForm(false)}>
                Fechar
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  )
}

export default App
