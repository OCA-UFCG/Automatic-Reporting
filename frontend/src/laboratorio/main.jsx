import React, { Component, StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Laboratorio from './Laboratorio.jsx'
import './laboratorio.css'

// Um erro de render desmontava a página inteira e sobrava só o fundo (sugestões do
// editor sem a unidade, 24/11/2026). Agora sobra uma mensagem com o erro.
class SemTelaVazia extends Component {
  state = { erro: null }
  static getDerivedStateFromError(erro) {
    return { erro }
  }
  render() {
    if (!this.state.erro) return this.props.children
    return (
      <div className="empty" style={{ margin: 24 }}>
        <h2>O TemaLab encontrou um erro</h2>
        <p>O texto que estava na caixa de edição se perdeu. As versões salvas com "Pronto" continuam no rascunho do navegador.</p>
        <p className="muted"><code>{String(this.state.erro?.message ?? this.state.erro)}</code></p>
        <button className="btn pri" onClick={() => location.reload()}>Recarregar</button>
      </div>
    )
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SemTelaVazia>
      <Laboratorio />
    </SemTelaVazia>
  </StrictMode>
)
