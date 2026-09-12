import React, { useCallback, useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import { Icone } from '../icones.jsx'

// O worker do pdf.js vem do pacote, empacotado pelo Vite — e não de uma CDN,
// como no portal. O painel roda na rede interna da Sudene, onde nem sempre há
// saída para a internet; um worker que não carrega deixaria a prévia em branco
// sem dizer por quê.
//
// O import é dinâmico por dois motivos: o worker (1,4 MB) só é baixado quando
// alguém abre a prévia, e o `?url` — sintaxe do Vite — fica fora do caminho do
// esbuild, que monta o teste de fumaça (`npm run smoke -w admin`) para Node e
// não saberia resolvê-lo.
let workerPronto = null;

function prepararWorker() {
  if (!workerPronto) {
    workerPronto = import('pdfjs-dist/build/pdf.worker.min.mjs?url').then((modulo) => {
      GlobalWorkerOptions.workerSrc = modulo.default;
    });
  }
  return workerPronto;
}

// Esta tela é a mesma do portal: `PdfViewer` do data-nordeste-frontend, que é
// o que o editor já conhece do beta. Os nomes das classes CSS foram mantidos
// (`pdf-viewer-*`, `pdf-toolbar-*`) justamente para que o estilo copiado de lá
// continue reconhecível lado a lado com o original.

const PASSO_DE_ZOOM = 0.25;
const ZOOM_MINIMO = 0.5;
const ZOOM_MAXIMO = 3;
const ZOOM_INICIAL = 1;

export default function VisualizadorDePdf({ urlDoPdf, nomeDoArquivo }) {
  const containerRef = useRef(null);
  const [documento, setDocumento] = useState(null);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [totalDePaginas, setTotalDePaginas] = useState(0);
  const [paginas, setPaginas] = useState([]);
  const [zoom, setZoom] = useState(ZOOM_INICIAL);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    let cancelado = false;

    setDocumento(null);
    setTotalDePaginas(0);
    setPaginas([]);
    setPaginaAtual(1);
    setErro(false);

    prepararWorker()
      .then(() => getDocument({ url: urlDoPdf, cMapPacked: true }).promise)
      .then(
        (doc) => {
          if (cancelado) return;
          setDocumento(doc);
          setTotalDePaginas(doc.numPages);
          setPaginas(Array.from({ length: doc.numPages }, (_, i) => i + 1));
        },
        () => {
          if (!cancelado) setErro(true);
        },
      );

    return () => {
      cancelado = true;
    };
  }, [urlDoPdf]);

  const irParaPagina = (numero) => {
    const elemento = document.getElementById(`pdf-pagina-${numero}`);
    if (elemento) elemento.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const alternarTelaCheia = () => {
    if (!containerRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
      setZoom(ZOOM_INICIAL);
      containerRef.current.classList.remove('pdf-viewer-fullscreen');
    } else {
      containerRef.current.requestFullscreen();
      containerRef.current.classList.add('pdf-viewer-fullscreen');
    }
  };

  const aoFicarVisivel = useCallback((numero) => setPaginaAtual(numero), []);

  if (erro) {
    return (
      <div className="pdf-viewer-error" role="alert">
        Não foi possível abrir o PDF da prévia. Gere de novo; se repetir, veja o log da API.
      </div>
    );
  }

  if (!documento) {
    return (
      <div className="pdf-viewer-loading" aria-live="polite">
        <div className="pdf-viewer-spinner" />
        <span>Abrindo o documento…</span>
      </div>
    );
  }

  return (
    <div className="pdf-viewer" ref={containerRef}>
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-left">
          <span className="pdf-toolbar-filename" title={nomeDoArquivo}>{nomeDoArquivo}</span>
        </div>

        <div className="pdf-toolbar-center">
          <div className="pdf-toolbar-page-indicator">
            <button
              type="button"
              className="pdf-toolbar-btn-page"
              onClick={() => irParaPagina(Math.max(1, paginaAtual - 1))}
              disabled={paginaAtual <= 1}
              aria-label="Página anterior"
            >
              <span className="pdf-toolbar-page-nav">‹</span>
            </button>
            <div className="pdf-toolbar-page-field">
              <span className="pdf-toolbar-page-current">{paginaAtual}</span>
              <span className="pdf-toolbar-page-sep">/</span>
              <span className="pdf-toolbar-page-total">{totalDePaginas}</span>
            </div>
            <button
              type="button"
              className="pdf-toolbar-btn-page"
              onClick={() => irParaPagina(Math.min(totalDePaginas, paginaAtual + 1))}
              disabled={paginaAtual >= totalDePaginas}
              aria-label="Próxima página"
            >
              <span className="pdf-toolbar-page-nav">›</span>
            </button>
          </div>

          <div className="pdf-toolbar-zoom">
            <button
              type="button"
              className="pdf-toolbar-btn-icon"
              onClick={() => setZoom((z) => Math.max(ZOOM_MINIMO, z - PASSO_DE_ZOOM))}
              disabled={zoom <= ZOOM_MINIMO}
              aria-label="Diminuir zoom"
            >
              <Icone nome="zoom-out" />
            </button>
            <div className="pdf-toolbar-zoom-field">
              <span className="pdf-toolbar-zoom-level">{Math.round(zoom * 100)}%</span>
            </div>
            <button
              type="button"
              className="pdf-toolbar-btn-icon"
              onClick={() => setZoom((z) => Math.min(ZOOM_MAXIMO, z + PASSO_DE_ZOOM))}
              disabled={zoom >= ZOOM_MAXIMO}
              aria-label="Aumentar zoom"
            >
              <Icone nome="zoom-in" />
            </button>
          </div>

          <button
            type="button"
            className="pdf-toolbar-btn-icon"
            onClick={alternarTelaCheia}
            aria-label="Tela cheia"
            title="Tela cheia"
          >
            <Icone nome="fullscreen" />
          </button>
        </div>

        <div className="pdf-toolbar-right">
          <a
            className="pdf-toolbar-download"
            href={urlDoPdf}
            download={nomeDoArquivo}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Icone nome="download" className="icone-download" />
            <span>Baixar PDF</span>
          </a>
        </div>
      </div>

      <div className="pdf-viewer-canvas-wrapper" style={{ scrollBehavior: 'smooth' }}>
        <div className="pdf-viewer-pages-column">
          {paginas.map((numero) => (
            <PaginaDoPdf
              key={numero}
              documento={documento}
              numero={numero}
              escala={zoom}
              aoFicarVisivel={aoFicarVisivel}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function PaginaDoPdf({ documento, numero, escala, aoFicarVisivel }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const tarefaRef = useRef(null);

  // Só desenha quando a página chega perto da viewport. Um relatório de
  // macrotema passa de vinte páginas; desenhar todas de uma vez trava a aba.
  const [deveDesenhar, setDeveDesenhar] = useState(false);

  useEffect(() => {
    if (!deveDesenhar) return undefined;
    let cancelado = false;

    const desenhar = async () => {
      if (!documento || !canvasRef.current || !containerRef.current) return;

      if (tarefaRef.current) {
        tarefaRef.current.cancel();
        tarefaRef.current = null;
      }

      try {
        const pagina = await documento.getPage(numero);
        if (cancelado) return;

        // A escala efetiva sai da largura do container: em tela estreita a
        // página encolhe para caber, em vez de ser espremida por CSS — que
        // distorceria o canvas.
        const larguraDisponivel = containerRef.current.clientWidth;
        const viewportBase = pagina.getViewport({ scale: 1 });
        const larguraComZoom = viewportBase.width * escala;
        const precisaCaber = larguraDisponivel > 0 && larguraComZoom > larguraDisponivel;
        const larguraFinal = precisaCaber ? larguraDisponivel : larguraComZoom;
        const escalaEfetiva = larguraFinal / viewportBase.width;

        const canvas = canvasRef.current;
        const contexto = canvas.getContext('2d');
        if (!contexto) return;

        // Teto no devicePixelRatio: sem ele cada página custa memória de vídeo
        // proporcional ao quadrado do DPR, sem ganho visível de nitidez.
        const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        const viewportDesenho = pagina.getViewport({ scale: escalaEfetiva * dpr });
        const viewportExibicao = pagina.getViewport({ scale: escalaEfetiva });

        canvas.width = Math.round(viewportDesenho.width);
        canvas.height = Math.round(viewportDesenho.height);
        canvas.style.width = `${Math.round(viewportExibicao.width)}px`;
        canvas.style.height = `${Math.round(viewportExibicao.height)}px`;
        contexto.setTransform(1, 0, 0, 1, 0, 0);

        const tarefa = pagina.render({ canvasContext: contexto, viewport: viewportDesenho });
        tarefaRef.current = tarefa;
        await tarefa.promise;
      } catch (err) {
        // Cancelar um desenho em andamento é o caminho normal quando o zoom
        // muda no meio; não é erro.
        if (!String(err?.message || '').includes('Rendering cancelled')) {
          console.error(`Falha ao desenhar a página ${numero} da prévia`, err);
        }
      }
    };

    desenhar();

    return () => {
      cancelado = true;
      if (tarefaRef.current) tarefaRef.current.cancel();
    };
  }, [documento, numero, escala, deveDesenhar]);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    // Dois observadores separados de propósito: um adianta o desenho numa
    // janela de 500px ao redor da viewport, o outro só diz qual página está na
    // tela para o contador da barra.
    const observadorDeAntecipacao = new IntersectionObserver(
      (entradas) => {
        if (entradas[0].isIntersecting) {
          setDeveDesenhar(true);
          observadorDeAntecipacao.disconnect();
        }
      },
      { rootMargin: '500px' },
    );

    const observadorDeVisibilidade = new IntersectionObserver(
      (entradas) => {
        if (entradas[0].isIntersecting) aoFicarVisivel(numero);
      },
      { threshold: 0.5 },
    );

    observadorDeAntecipacao.observe(containerRef.current);
    observadorDeVisibilidade.observe(containerRef.current);

    return () => {
      observadorDeAntecipacao.disconnect();
      observadorDeVisibilidade.disconnect();
    };
  }, [numero, aoFicarVisivel]);

  return (
    <div id={`pdf-pagina-${numero}`} ref={containerRef} style={{ width: '100%' }}>
      {deveDesenhar ? (
        <canvas ref={canvasRef} className="pdf-viewer-canvas" />
      ) : (
        // O placeholder guarda a altura aproximada (proporção A4) para o
        // scroll não pular quando o canvas monta.
        <div className="pdf-viewer-placeholder" aria-hidden="true" />
      )}
    </div>
  );
}
