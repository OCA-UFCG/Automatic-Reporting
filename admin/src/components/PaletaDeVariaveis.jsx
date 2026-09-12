import React, { useState } from 'react'

// Os campos aparecem com o nome exato da coluna do banco — `nm_mun`,
// `pri_nivel_per` — e não com uma versão "amigável". Quem opera o painel
// conversa direto com quem mantém as views do Data Nordeste; quando precisa
// perguntar "de onde vem esse número?", precisa citar o identificador que a
// outra pessoa reconhece. Um rótulo embelezado quebra essa conversa.

export default function PaletaDeVariaveis({ campos, graficos, origem, aviso, aoInserir, aoInserirGrafico, usados }) {
  const [abaAtiva, setAbaAtiva] = useState('campos');
  const [busca, setBusca] = useState('');

  const termo = busca.trim().toLowerCase();
  const filtrados = termo
    ? campos.filter((c) => c.campo.toLowerCase().includes(termo))
    : campos;

  return (
    <aside className="paleta">
      <nav className="paleta-abas">
        <button
          type="button"
          className={abaAtiva === 'campos' ? 'ativa' : ''}
          onClick={() => setAbaAtiva('campos')}
        >
          Variáveis <span className="contagem">{campos.length}</span>
        </button>
        <button
          type="button"
          className={abaAtiva === 'graficos' ? 'ativa' : ''}
          onClick={() => setAbaAtiva('graficos')}
        >
          Gráficos <span className="contagem">{graficos.length}</span>
        </button>
      </nav>

      {abaAtiva === 'campos' && (
        <>
          <input
            className="busca"
            type="search"
            placeholder="Buscar variável…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
          {aviso && (
            /* O texto vem do /manifesto: só o backend sabe se a lista veio da
               view, do CSV ou do cache, e cada caso quer uma frase diferente.
               Duplicar a mensagem aqui já deixou a tela dizendo "lista parcial"
               quando a lista estava completa, vinda do CSV. */
            <p className={origem === 'cache' ? 'paleta-aviso' : 'paleta-aviso brando'}>
              {aviso}
            </p>
          )}
          <ul className="lista-campos">
            {filtrados.map((campo) => (
              <li key={campo.campo}>
                <button type="button" onClick={() => aoInserir(campo)} title={campo.origem}>
                  <span className="campo-nome">{campo.campo}</span>
                  <span className="campo-meta">
                    {campo.tipo !== 'desconhecido' && <em>{campo.tipo}</em>}
                    {usados?.has(campo.campo) && (
                      <span className="usado" title="já usado neste tema">●</span>
                    )}
                  </span>
                </button>
              </li>
            ))}
            {filtrados.length === 0 && <li className="vazio">Nenhuma variável com esse nome.</li>}
          </ul>
        </>
      )}

      {abaAtiva === 'graficos' && (
        <ul className="lista-campos">
          {graficos.map((grafico) => (
            <li key={grafico.nome}>
              <button type="button" onClick={() => aoInserirGrafico(grafico)} title={grafico.legenda}>
                <span className="campo-nome">{grafico.nome}</span>
                {grafico.legenda && <span className="campo-meta">{grafico.legenda}</span>}
              </button>
            </li>
          ))}
          {graficos.length === 0 && <li className="vazio">Nenhum gráfico registrado para este tema.</li>}
        </ul>
      )}
    </aside>
  );
}
