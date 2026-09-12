import React from 'react'
import { SLOTS_MOLDURA, TIPOS_CRIAVEIS, resumoDoBloco, temFilhos } from '../contrato.js'

const ICONE = Object.fromEntries(TIPOS_CRIAVEIS.map((t) => [t.tipo, t.icone]));

function Linha({ bloco, nivel, selecionado, aoSelecionar, aoMover, aoRemover, aoAdicionarFilho }) {
  return (
    <>
      <li
        className={`bloco-linha${selecionado === bloco.id ? ' selecionada' : ''}`}
        style={{ '--nivel': nivel }}
      >
        <button type="button" className="bloco-alvo" onClick={() => aoSelecionar(bloco.id)}>
          <span className="bloco-icone" aria-hidden="true">{ICONE[bloco.tipo] || '¶'}</span>
          <span className="bloco-resumo">{resumoDoBloco(bloco)}</span>
          {bloco.regra && (
            <span className="selo-regra" title="Este bloco só aparece quando a regra é atendida">
              regra
            </span>
          )}
        </button>
        <span className="bloco-botoes">
          {temFilhos(bloco) && (
            <button type="button" className="icone" title="Adicionar dentro" onClick={() => aoAdicionarFilho(bloco.id)}>+</button>
          )}
          <button type="button" className="icone" title="Subir" onClick={() => aoMover(bloco.id, -1)}>↑</button>
          <button type="button" className="icone" title="Descer" onClick={() => aoMover(bloco.id, 1)}>↓</button>
          <button type="button" className="icone perigo" title="Remover" onClick={() => aoRemover(bloco.id)}>×</button>
        </span>
      </li>
      {(bloco.blocos || []).map((filho) => (
        <Linha
          key={filho.id}
          bloco={filho}
          nivel={nivel + 1}
          selecionado={selecionado}
          aoSelecionar={aoSelecionar}
          aoMover={aoMover}
          aoRemover={aoRemover}
          aoAdicionarFilho={aoAdicionarFilho}
        />
      ))}
    </>
  );
}

function Grupo({ titulo, ajuda, blocos, ...resto }) {
  return (
    <section className="grupo-blocos">
      <header>
        <h3>{titulo}</h3>
        {ajuda && <p>{ajuda}</p>}
      </header>
      <ul>
        {blocos.map((bloco) => (
          <Linha key={bloco.id} bloco={bloco} nivel={0} {...resto} />
        ))}
        {!blocos.length && <li className="vazio">vazio</li>}
      </ul>
      <button type="button" className="secundario largura-total" onClick={resto.aoAdicionar}>
        + bloco
      </button>
    </section>
  );
}

export default function ArvoreDeBlocos({ contrato, selecionado, aoSelecionar, aoMover, aoRemover, aoAdicionar, aoAdicionarFilho }) {
  const comuns = { selecionado, aoSelecionar, aoMover, aoRemover, aoAdicionarFilho };

  return (
    <div className="arvore">
      <Grupo
        titulo="Corpo do tema"
        ajuda="A seção do relatório. O operador cria, reordena e apaga à vontade."
        blocos={contrato.corpo?.blocos || []}
        aoAdicionar={() => aoAdicionar({ slot: 'corpo' })}
        {...comuns}
      />

      <p className="rotulo-moldura">Moldura — lugares fixos no layout</p>
      {SLOTS_MOLDURA.map((slot) => (
        <Grupo
          key={slot.chave}
          titulo={slot.nome}
          ajuda={slot.ajuda}
          blocos={contrato.moldura?.[slot.chave]?.blocos || []}
          aoAdicionar={() => aoAdicionar({ slot: slot.chave })}
          {...comuns}
        />
      ))}
    </div>
  );
}
