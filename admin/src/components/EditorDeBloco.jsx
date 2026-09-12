import React, { useRef } from 'react'
import EditorDeTexto from './EditorDeTexto.jsx'
import ConstrutorDeRegra from './ConstrutorDeRegra.jsx'
import { TIPOS_CRIAVEIS, temConteudo, temFilhos } from '../contrato.js'

const NOME_DO_TIPO = Object.fromEntries(TIPOS_CRIAVEIS.map((t) => [t.tipo, t.nome]));

export default function EditorDeBloco({
  bloco, aoMudar, manifesto, campos, graficos, rotuloDe, registrarEditor,
}) {
  const refTexto = useRef(null);
  const refsItens = useRef({});

  if (!bloco) {
    return (
      <div className="editor-vazio">
        <p>Escolha um bloco à esquerda para editar, ou crie um novo.</p>
      </div>
    );
  }

  return (
    <div className="editor-bloco">
      <header className="editor-cabecalho">
        <h2>{NOME_DO_TIPO[bloco.tipo] || bloco.tipo}</h2>
        <code className="id-bloco" title="Identificador do bloco no contrato">{bloco.id}</code>
      </header>

      {temFilhos(bloco) && (
        <label className="campo-formulario">
          <span>Título</span>
          <input
            type="text"
            value={bloco.titulo || ''}
            placeholder={bloco.tipo === 'caixa' ? 'Ex.: Fontes' : 'Ex.: Síntese'}
            onChange={(e) => aoMudar({ ...bloco, titulo: e.target.value })}
          />
          <small>
            {bloco.tipo === 'caixa'
              ? 'Abre uma caixa destacada no fim da seção.'
              : 'Sai como título; deixe vazio para só agrupar blocos sob uma mesma regra.'}
          </small>
        </label>
      )}

      {temConteudo(bloco) && (
        <label className="campo-formulario">
          <span>Texto</span>
          <EditorDeTexto
            ref={(instancia) => { refTexto.current = instancia; registrarEditor(instancia); }}
            chave={bloco.id}
            conteudo={bloco.conteudo}
            rotuloDe={rotuloDe}
            aoMudar={(conteudo) => aoMudar({ ...bloco, conteudo })}
            aoFocar={() => registrarEditor(refTexto.current)}
            placeholder="Escreva o parágrafo e clique nas variáveis ao lado para inseri-las."
          />
          <small>As variáveis entram como etiquetas, clicando na lista à direita.</small>
        </label>
      )}

      {bloco.tipo === 'lista' && (
        <div className="campo-formulario">
          <span>Itens</span>
          {(bloco.itens || []).map((item, i) => (
            <div className="item-lista" key={`${bloco.id}-${i}`}>
              <EditorDeTexto
                ref={(instancia) => { refsItens.current[i] = instancia; }}
                chave={`${bloco.id}-${i}`}
                conteudo={item}
                rotuloDe={rotuloDe}
                aoMudar={(conteudo) =>
                  aoMudar({ ...bloco, itens: bloco.itens.map((it, j) => (j === i ? conteudo : it)) })
                }
                aoFocar={() => registrarEditor(refsItens.current[i])}
                placeholder="Item da lista"
              />
              <button
                type="button" className="icone perigo" title="Remover item"
                onClick={() => aoMudar({ ...bloco, itens: bloco.itens.filter((_, j) => j !== i) })}
              >×</button>
            </div>
          ))}
          <button
            type="button" className="secundario"
            onClick={() => aoMudar({ ...bloco, itens: [...(bloco.itens || []), [{ t: 'texto', v: '' }]] })}
          >+ item</button>
        </div>
      )}

      {bloco.tipo === 'grafico' && (
        <label className="campo-formulario">
          <span>Gráfico</span>
          <select
            value={bloco.grafico || ''}
            onChange={(e) => aoMudar({ ...bloco, grafico: e.target.value })}
          >
            <option value="">— escolha —</option>
            {graficos.map((grafico) => (
              <option key={grafico.nome} value={grafico.nome}>{grafico.rotulo}</option>
            ))}
            {bloco.grafico && !graficos.some((g) => g.nome === bloco.grafico) && (
              <option value={bloco.grafico}>{bloco.grafico} (não registrado)</option>
            )}
          </select>
          <small>
            Os gráficos são gerados em Python. Esta lista é a dos que já existem para o tema —
            um gráfico novo é trabalho de dev, não de edição.
          </small>
        </label>
      )}

      <section className="bloco-regra">
        <h3>Quando este bloco aparece</h3>
        <ConstrutorDeRegra
          regra={bloco.regra}
          campos={campos}
          manifesto={manifesto}
          aoMudar={(regra) => aoMudar({ ...bloco, regra })}
        />
      </section>
    </div>
  );
}
