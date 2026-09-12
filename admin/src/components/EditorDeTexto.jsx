import React, { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'

// Editor de uma linha de prosa. As variáveis são "chips": blocos indivisíveis
// que o editor insere clicando na lista ao lado, nunca digitando "$campo".
// É a diferença que importa em relação ao Google Docs — um chip não tem como
// estar com o nome errado, porque ele veio do manifesto.
//
// O campo é *não controlado* de propósito: repintar o HTML a cada tecla
// destruiria a posição do cursor e o histórico de desfazer do navegador. O
// conteúdo só é repintado quando muda o bloco que está sendo editado.

const ZERO_WIDTH = '​';

function criarChip(campo, rotulo) {
  const chip = document.createElement('span');
  chip.className = 'chip';
  chip.contentEditable = 'false';
  chip.dataset.campo = campo;
  chip.textContent = rotulo || campo.split('.').pop();
  chip.title = campo;
  return chip;
}

function pintar(elemento, conteudo, rotuloDe) {
  elemento.innerHTML = '';
  (conteudo || []).forEach((trecho) => {
    if (trecho.t === 'var') {
      elemento.appendChild(criarChip(trecho.campo, rotuloDe?.(trecho.campo)));
      // Espaço de largura zero depois do chip: sem ele, não há onde pousar o
      // cursor quando o chip é o último nó da linha.
      elemento.appendChild(document.createTextNode(ZERO_WIDTH));
    } else {
      elemento.appendChild(document.createTextNode(trecho.v ?? ''));
    }
  });
}

function serializar(elemento) {
  const trechos = [];
  const empurrarTexto = (texto) => {
    const limpo = texto.replaceAll(ZERO_WIDTH, '');
    if (!limpo) return;
    const ultimo = trechos[trechos.length - 1];
    if (ultimo?.t === 'texto') ultimo.v += limpo;
    else trechos.push({ t: 'texto', v: limpo });
  };

  const percorrer = (no) => {
    no.childNodes.forEach((filho) => {
      if (filho.nodeType === Node.TEXT_NODE) {
        empurrarTexto(filho.nodeValue || '');
      } else if (filho.dataset?.campo) {
        trechos.push({ t: 'var', campo: filho.dataset.campo });
      } else if (filho.tagName === 'BR') {
        empurrarTexto(' ');
      } else {
        percorrer(filho);
      }
    });
  };

  percorrer(elemento);
  return trechos.length ? trechos : [{ t: 'texto', v: '' }];
}

const EditorDeTexto = forwardRef(function EditorDeTexto(
  { chave, conteudo, aoMudar, rotuloDe, placeholder, aoFocar },
  ref
) {
  const caixa = useRef(null);
  const intervaloSalvo = useRef(null);

  useEffect(() => {
    if (caixa.current) pintar(caixa.current, conteudo, rotuloDe);
    // Depende só de `chave`: repintar quando o texto muda desfaria a digitação.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave]);

  const guardarPosicao = () => {
    const selecao = window.getSelection();
    if (!selecao?.rangeCount) return;
    const intervalo = selecao.getRangeAt(0);
    if (caixa.current?.contains(intervalo.commonAncestorContainer)) {
      intervaloSalvo.current = intervalo.cloneRange();
    }
  };

  const emitir = () => {
    if (caixa.current) aoMudar(serializar(caixa.current));
  };

  useImperativeHandle(ref, () => ({
    inserirVariavel(campo, rotulo) {
      const elemento = caixa.current;
      if (!elemento) return;
      elemento.focus();

      // Clicar na lista de variáveis tira o foco do texto; por isso a posição
      // do cursor é guardada a cada interação e restaurada aqui.
      const selecao = window.getSelection();
      let intervalo = intervaloSalvo.current;
      if (!intervalo || !elemento.contains(intervalo.commonAncestorContainer)) {
        intervalo = document.createRange();
        intervalo.selectNodeContents(elemento);
        intervalo.collapse(false);
      }

      intervalo.deleteContents();
      const chip = criarChip(campo, rotulo);
      const depois = document.createTextNode(ZERO_WIDTH);
      intervalo.insertNode(depois);
      intervalo.insertNode(chip);

      const novo = document.createRange();
      novo.setStartAfter(depois);
      novo.collapse(true);
      selecao.removeAllRanges();
      selecao.addRange(novo);
      intervaloSalvo.current = novo.cloneRange();
      emitir();
    },
  }));

  return (
    <div
      ref={caixa}
      className="editor-texto"
      contentEditable
      suppressContentEditableWarning
      role="textbox"
      aria-multiline="false"
      data-placeholder={placeholder || 'Escreva aqui…'}
      onInput={emitir}
      onBlur={() => { guardarPosicao(); emitir(); }}
      onKeyUp={guardarPosicao}
      onMouseUp={guardarPosicao}
      onFocus={() => { guardarPosicao(); aoFocar?.(); }}
      onKeyDown={(evento) => {
        // Enter viraria <div> ou <br> dentro do parágrafo; cada bloco é uma
        // unidade de texto, e quebrar linha aqui é sempre engano.
        if (evento.key === 'Enter') evento.preventDefault();
      }}
      onPaste={(evento) => {
        // Colar do Word/Docs traz HTML com estilo embutido que estragaria a
        // serialização; só o texto interessa.
        evento.preventDefault();
        const texto = evento.clipboardData.getData('text/plain').replace(/\s+/g, ' ');
        document.execCommand('insertText', false, texto);
      }}
    />
  );
});

export default EditorDeTexto;
