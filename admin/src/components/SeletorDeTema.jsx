import React from 'react'
import { IconeDoMacrotema } from '../icones.jsx'

function estado(tema) {
  if (!tema.contrato) return { texto: 'não importado', classe: 'ausente' };
  return { texto: `versão ${tema.contrato.versao}`, classe: 'pronto' };
}

export default function SeletorDeTema({ temas, aoEscolher, carregando }) {
  return (
    <div className="seletor">
      <header className="seletor-topo">
        <h1>Macrotemas</h1>
        <p>Escolha o tema para editar. Cada um tem seu próprio contrato e seu próprio histórico.</p>
      </header>

      {carregando && <p className="dica">Carregando…</p>}

      <ul className="grade-temas">
        {temas.map((tema) => {
          const situacao = estado(tema);
          return (
            <li key={tema.slug}>
              <button type="button" onClick={() => aoEscolher(tema.slug)}>
                {/* Ícone branco sobre um quadrado da cor do tema — é como o
                    portal desenha o mesmo ícone em `CategoryCard.tsx`. Colorido
                    sobre o branco do cartão, o amarelo de Educação e o verde
                    limão de Meio Ambiente ficavam quase invisíveis. */}
                <span className="tema-cabecalho">
                  <span className="tema-icone" style={{ background: tema.cor }}>
                    <IconeDoMacrotema slug={tema.slug} />
                  </span>
                  <span className="tema-nome">{tema.nome}</span>
                </span>
                <span className="tema-meta">
                  <span className={`situacao ${situacao.classe}`}>{situacao.texto}</span>
                  <span
                    className={`fonte ${tema.fonte_editorial}`}
                    title={
                      tema.fonte_editorial === 'painel'
                        ? 'Os relatórios deste tema já usam o contrato do painel.'
                        : 'Os relatórios deste tema ainda vêm do Google Doc. Editar aqui não muda o que sai em produção.'
                    }
                  >
                    {tema.fonte_editorial === 'painel' ? 'no ar pelo painel' : 'ainda pelo Doc'}
                  </span>
                </span>
                {tema.contrato?.publicado_por && (
                  <span className="tema-autor">
                    por {tema.contrato.publicado_por}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
