import React, { useEffect, useMemo, useState } from "react";

// Default to same-origin when served by the API (Docker/prod).
// In dev (Vite on :5173), set VITE_API_BASE_URL=http://127.0.0.1:8000.
const API_BASE = import.meta.env.VITE_API_BASE_URL || window.location.origin
const MACROTEMAS = [
  'Demografia'
]

function App() {
  const [view, setView] = useState("home");
  const [cities, setCities] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedMacrotema, setSelectedMacrotema] = useState(MACROTEMAS[0]);
  const [selectedCity, setSelectedCity] = useState("");
  const [citySearch, setCitySearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [reportsError, setReportsError] = useState("");
  const [reportToDelete, setReportToDelete] = useState(null);

  useEffect(() => {
    async function fetchCities() {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/cities`);
        if (!response.ok) {
          throw new Error("Falha ao carregar cidades");
        }
        const data = await response.json();
        setCities(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.message || "Erro ao carregar cidades");
      } finally {
        setLoading(false);
      }
    }

    fetchCities();
  }, []);

  useEffect(() => {
    fetchReports();
  }, []);

  async function fetchReports() {
    try {
      setReportsLoading(true);
      setReportsError("");
      const response = await fetch(`${API_BASE}/relatorios`);
      if (!response.ok) {
        throw new Error("Falha ao carregar relatorios");
      }
      const data = await response.json();
      setReports(Array.isArray(data) ? data : []);
    } catch (err) {
      setReportsError(err.message || "Erro ao carregar relatórios");
    } finally {
      setReportsLoading(false);
    }
  }

  async function deleteReport(fileName) {
    if (!fileName) return;

    try {
      const response = await fetch(`${API_BASE}/relatorios/${encodeURIComponent(fileName)}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Falha ao apagar relatório");
      }

      await fetchReports();
      setReportToDelete(null);
    } catch (err) {
      setReportsError(err.message || "Erro ao apagar relatório");
    }
  }

  function requestDeleteReport(report) {
    setReportToDelete(report);
  }

  const cityCount = useMemo(() => cities.length, [cities]);
  const filteredCities = useMemo(() => {
    const term = citySearch.trim().toLowerCase();
    if (!term) return cities;
    return cities.filter((city) => city.toLowerCase().includes(term));
  }, [cities, citySearch]);

  async function openReport() {
    if (!selectedCity) {
      return;
    }

    const url = `${API_BASE}/relatorio/${encodeURIComponent(selectedCity)}`;
    window.open(url, "_blank");
    setShowForm(false);

    let found = false;
    let attempts = 0;
    const maxAttempts = 60;

    const pollInterval = setInterval(async () => {
      attempts++;
      try {
        const response = await fetch(`${API_BASE}/relatorios`);
        if (response.ok) {
          const data = await response.json();
          const newReports = Array.isArray(data) ? data : [];
          const reportExists = newReports.some(
            (report) => report.cidade.toLowerCase() === selectedCity.toLowerCase()
          );
          if (reportExists) {
            found = true;
            setReports(newReports);
            clearInterval(pollInterval);
          }
        }
      } catch (err) {
        console.error("Error polling for reports:", err);
      }

      if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        fetchReports();
      }
    }, 1000);
  }

  return (
    <main className="page-shell">
      {view === "reports" ? (
        <section className="reports-screen">
          <div className="reports-header">
            <h2>Relatórios gerados</h2>
            <button type="button" className="secondary-button" onClick={() => setView("home")}>
              Voltar
            </button>
          </div>

          <div className="reports-table-wrap">
            <table className="reports-table">
              <thead>
                <tr>
                  <th>Cidade</th>
                  <th>Data</th>
                  <th>Hora</th>
                  <th>Download</th>
                  <th>Lixeira</th>
                </tr>
              </thead>
              <tbody>
                {reportsLoading && (
                  <tr>
                    <td colSpan="5">Carregando relatórios...</td>
                  </tr>
                )}

                {reportsError && !reportsLoading && (
                  <tr>
                    <td colSpan="5" className="error">{reportsError}</td>
                  </tr>
                )}

                {!reportsLoading && !reportsError && reports.length === 0 && (
                  <tr>
                    <td colSpan="5">Nenhum relatório gerado ainda.</td>
                  </tr>
                )}

                {!reportsLoading && !reportsError && reports.map((report) => (
                  <tr key={report.arquivo_pdf}>
                    <td>{report.cidade}</td>
                    <td>{report.data}</td>
                    <td>{report.hora}</td>
                    <td>
                      <a className="report-button report-download-button" href={`${API_BASE}${report.pdf_url}`} download>
                        Download PDF
                      </a>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="trash-button"
                        onClick={() => requestDeleteReport(report)}
                        aria-label={`Apagar relatório ${report.cidade}`}
                        title="Apagar relatório"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-3.5l-1-1M18 7H6v12c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7z" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
      <section className="hero">
        <div>
          <span className="eyebrow">Sudene • Gerador de relatórios</span>
          <h1>Geração de relatório para Sudene</h1>
          <p className="subtitle">
            Escolha a cidade para montar o relatório de Demografia.
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
            <button
              type="button"
              className="secondary-button"
              onClick={() => {
                fetchReports();
                setView("reports");
              }}
            >
              Relatórios gerados
            </button>
            <div className="stat-pill">{cityCount} cidades disponíveis</div>
          </div>
        </div>

        <aside className="hero-card">
          <p className="hero-card-label">Macrotemas disponíveis</p>
          <div className="macrotema-tags">
            {MACROTEMAS.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        </aside>
      </section>
      )}

      {loading && <p className="status-text">Carregando cidades...</p>}
      {error && <p className="error">{error}</p>}

      {showForm && !loading && !error && (
        <div
          className="modal-backdrop"
          onClick={() => setShowForm(false)}
          role="presentation"
        >
          <section
            className="modal-card"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h2>Formulário de relatório</h2>
                <p>Selecione o macrotema e a cidade desejada.</p>
              </div>
              <button
                type="button"
                className="close-button"
                onClick={() => setShowForm(false)}
              >
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
                  className={`city-card ${selectedCity === city ? "city-card--active" : ""}`}
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
                <strong>{selectedCity || "Nenhuma selecionada"}</strong>
              </div>
            </div>

            <div className="actions">
              <button
                type="button"
                className="report-button"
                onClick={openReport}
                disabled={!selectedCity}
              >
                Gerar relatório
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setShowForm(false)}
              >
                Fechar
              </button>
            </div>
          </section>
        </div>
      )}

      {reportToDelete && (
        <div className="confirm-backdrop" role="presentation" onClick={() => setReportToDelete(null)}>
          <section className="confirm-modal" onClick={(event) => event.stopPropagation()}>
            <h3>Apagar relatório</h3>
            <p>
              Tem certeza que deseja apagar o relatório de <strong>{reportToDelete.cidade}</strong>?
            </p>
            <div className="confirm-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setReportToDelete(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="danger-button"
                onClick={() => deleteReport(reportToDelete.arquivo_pdf)}
              >
                Apagar
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

export default App;
