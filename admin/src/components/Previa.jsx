import React from 'react'
import VisualizadorDePdf from './VisualizadorDePdf.jsx'

// A prévia é o relatório de verdade: o backend roda `gerar_relatorio_handler`,
// o mesmo caminho que atende o portal, com o contrato ainda não publicado
// injetado no lugar da prosa. Capa, gráficos, mapa e SSR são os mesmos — o que
// aparece aqui é o que sai no PDF.
//
// E o que a tela mostra é o PDF, não o HTML, pelo mesmo visualizador do portal.
// Com o HTML solto na página faltavam justamente as três coisas que o editor
// usa para conferir: as logos do cabeçalho (que só existem em `@media print`),
// a quebra de páginas (que é do WeasyPrint) e o botão de baixar.

export default function Previa({ cidades, cidade, aoTrocarCidade, resultado, carregando, erro, aoGerar }) {
  const semCidade = !cidade.trim();
  const cidadeConhecida = !semCidade && cidades.includes(cidade.trim());

  return (
    <section className="previa">
      <header className="previa-cabecalho">
        <label>
          <span>Município</span>
          <input
            type="text" list="lista-cidades" value={cidade}
            onChange={(e) => aoTrocarCidade(e.target.value)}
            placeholder="Campina Grande (PB)"
            autoComplete="off"
          />
          <datalist id="lista-cidades">
            {cidades.map((nome) => <option key={nome} value={nome} />)}
          </datalist>
        </label>
        <button type="button" onClick={aoGerar} disabled={carregando || semCidade}>
          {carregando ? 'Gerando…' : 'Gerar relatório'}
        </button>
        {/* O botão desabilitado sem explicação já fez o operador achar que a
            ferramenta estava quebrada. Diga o que falta. */}
        {semCidade && <span className="dica-botao">Escolha um município para liberar</span>}
        {!semCidade && !cidadeConhecida && (
          <span className="dica-botao alerta">
            Município fora da lista — confira a grafia e o “(UF)”
          </span>
        )}
      </header>

      {erro && <p className="erro">{erro}</p>}
      {resultado?.aviso && <p className="cartao-info">{resultado.aviso}</p>}

      {resultado?.campos_nao_resolvidos?.length > 0 && (
        <details className="nao-resolvidos">
          <summary>
            {resultado.campos_nao_resolvidos.length} variável(is) sem valor neste município
          </summary>
          <p>
            Cada uma sai impressa como texto cru no relatório. Ou o campo não existe para esta
            cidade — e aí o bloco precisa de regra — ou o nome está errado.
          </p>
          <ul>
            {resultado.campos_nao_resolvidos.map((campo) => <li key={campo}><code>{campo}</code></li>)}
          </ul>
        </details>
      )}

      {carregando && (
        <div className="carregando-previa" role="status" aria-live="polite">
          <span aria-hidden="true" className="carregando-previa-spinner" />
          <p>Gerando o relatório…</p>
        </div>
      )}

      {resultado?.pdf_url && !carregando && (
        <VisualizadorDePdf
          urlDoPdf={resultado.pdf_url}
          nomeDoArquivo={resultado.arquivo_pdf || 'relatorio.pdf'}
        />
      )}

      {!resultado && !carregando && !erro && (
        <p className="cartao-info">
          Escolha um município e gere o relatório completo — é o mesmo que o portal publica,
          com o texto que você está editando agora.
        </p>
      )}
    </section>
  );
}
