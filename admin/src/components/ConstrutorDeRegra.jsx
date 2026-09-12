import React from 'react'

// Construtor de regra. O operador escolhe campo, comparação e valor em listas
// — nunca escreve a condição em português. É aqui que "Para quando ... :" deixa
// de ser prosa interpretada por regex e vira dado.

const ACOES = [
  { valor: 'esconder', rotulo: 'esconder o bloco' },
  { valor: 'mostrar', rotulo: 'mostrar assim mesmo' },
  { valor: 'texto_alternativo', rotulo: 'mostrar outro texto' },
];

function CondicaoEditavel({ condicao, operadores, campos, aoMudar, aoRemover }) {
  const operador = operadores.find((o) => o.op === condicao.op);
  const aridade = operador?.aridade ?? 1;
  const comparaComCampo =
    condicao.valor && typeof condicao.valor === 'object' && !Array.isArray(condicao.valor);

  const trocarOperador = (op) => {
    const novo = operadores.find((o) => o.op === op);
    const proximo = { ...condicao, op };
    if (novo?.aridade === 0) delete proximo.valor;
    else if (novo?.aridade === 2) proximo.valor = [0, 0];
    else if (Array.isArray(condicao.valor) || condicao.valor === undefined) proximo.valor = 0;
    aoMudar(proximo);
  };

  return (
    <div className="condicao">
      <select
        aria-label="Campo"
        value={condicao.campo}
        onChange={(e) => aoMudar({ ...condicao, campo: e.target.value })}
      >
        {!campos.some((c) => c.campo === condicao.campo) && (
          <option value={condicao.campo}>{condicao.campo} (fora do manifesto)</option>
        )}
        {campos.map((campo) => (
          <option key={campo.campo} value={campo.campo}>{campo.rotulo}</option>
        ))}
      </select>

      <select
        aria-label="Comparação"
        value={condicao.op}
        onChange={(e) => trocarOperador(e.target.value)}
      >
        {operadores.map((op) => (
          <option key={op.op} value={op.op}>{op.rotulo}</option>
        ))}
      </select>

      {aridade === 2 && (
        <span className="faixa">
          <input
            type="number" aria-label="De"
            value={condicao.valor?.[0] ?? 0}
            onChange={(e) => aoMudar({ ...condicao, valor: [Number(e.target.value), condicao.valor?.[1] ?? 0] })}
          />
          <span className="e">e</span>
          <input
            type="number" aria-label="Até"
            value={condicao.valor?.[1] ?? 0}
            onChange={(e) => aoMudar({ ...condicao, valor: [condicao.valor?.[0] ?? 0, Number(e.target.value)] })}
          />
        </span>
      )}

      {aridade === 1 && !comparaComCampo && (
        <input
          type="number" aria-label="Valor"
          value={condicao.valor ?? 0}
          onChange={(e) => aoMudar({ ...condicao, valor: Number(e.target.value) })}
        />
      )}

      {aridade === 1 && comparaComCampo && (
        <select
          aria-label="Campo de comparação"
          value={condicao.valor.campo}
          onChange={(e) => aoMudar({ ...condicao, valor: { campo: e.target.value } })}
        >
          {campos.map((campo) => (
            <option key={campo.campo} value={campo.campo}>{campo.rotulo}</option>
          ))}
        </select>
      )}

      {aridade === 1 && (
        <button
          type="button"
          className="link"
          title="Comparar com outro campo em vez de um número fixo"
          onClick={() =>
            aoMudar({
              ...condicao,
              valor: comparaComCampo ? 0 : { campo: campos[0]?.campo || condicao.campo },
            })
          }
        >
          {comparaComCampo ? 'usar número' : 'usar outro campo'}
        </button>
      )}

      <button type="button" className="icone perigo" onClick={aoRemover} title="Remover condição">
        ×
      </button>
    </div>
  );
}

export default function ConstrutorDeRegra({ regra, aoMudar, manifesto, campos }) {
  const operadores = manifesto?.operadores || [];
  const condicoes = regra?.condicoes || [];
  const semDado = regra?.sem_dado || { acao: 'esconder' };

  const mudarCondicoes = (novas) => aoMudar({ ...(regra || {}), condicoes: novas });

  if (!regra) {
    return (
      <div className="regra-vazia">
        <p>Este bloco aparece em <strong>todos</strong> os municípios.</p>
        <button
          type="button"
          className="secundario"
          disabled={!campos.length}
          onClick={() =>
            aoMudar({
              condicoes: [{ campo: campos[0]?.campo || '', op: 'maior', valor: 0 }],
              sem_dado: { acao: 'esconder' },
            })
          }
        >
          Só mostrar em certos municípios…
        </button>
        {!campos.length && (
          <p className="aviso-inline">Sem campos no manifesto para montar uma regra.</p>
        )}
      </div>
    );
  }

  return (
    <div className="regra">
      <p className="regra-cabecalho">
        Aparece quando <strong>todas</strong> estas condições forem verdadeiras:
      </p>

      {condicoes.map((condicao, i) => (
        <CondicaoEditavel
          key={i}
          condicao={condicao}
          operadores={operadores}
          campos={campos}
          aoMudar={(nova) => mudarCondicoes(condicoes.map((c, j) => (j === i ? nova : c)))}
          aoRemover={() => {
            const restantes = condicoes.filter((_, j) => j !== i);
            // Regra sem nenhuma condição não é regra: o bloco volta a aparecer
            // sempre, que é o que a pessoa quis dizer ao remover a última.
            if (!restantes.length) aoMudar(null);
            else mudarCondicoes(restantes);
          }}
        />
      ))}

      <div className="regra-acoes">
        <button
          type="button"
          className="secundario"
          onClick={() =>
            mudarCondicoes([...condicoes, { campo: campos[0]?.campo || '', op: 'maior', valor: 0 }])
          }
        >
          + condição
        </button>
        <button type="button" className="link" onClick={() => aoMudar(null)}>
          mostrar sempre
        </button>
      </div>

      <div className="sem-dado">
        <label>
          Quando o município não tiver o dado,{' '}
          <select
            value={semDado.acao}
            onChange={(e) => {
              const acao = e.target.value;
              aoMudar({
                ...regra,
                sem_dado:
                  acao === 'texto_alternativo'
                    ? { acao, texto: semDado.texto || '' }
                    : { acao },
              });
            }}
          >
            {ACOES.map((acao) => (
              <option key={acao.valor} value={acao.valor}>{acao.rotulo}</option>
            ))}
          </select>
        </label>
        {semDado.acao === 'texto_alternativo' && (
          <textarea
            rows={2}
            placeholder="Ex.: Não foram encontrados registros para este município."
            value={semDado.texto || ''}
            onChange={(e) =>
              aoMudar({ ...regra, sem_dado: { acao: 'texto_alternativo', texto: e.target.value } })
            }
          />
        )}
      </div>
    </div>
  );
}
