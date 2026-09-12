import React from 'react'

// De onde sai a prosa deste macrotema no relatório que o portal entrega.
// O texto é escrito para quem opera: "Google Doc" e "este painel" são os dois
// lugares onde a pessoa escreve. O nome da variável de ambiente aparece só na
// explicação de por que o botão está travado — é vocabulário de quem administra
// o servidor, e fica separado de propósito.

const OPCOES = [
  { valor: 'docs', rotulo: 'Google Doc' },
  { valor: 'painel', rotulo: 'Este painel' },
];

export default function SeletorDeFonte({ tema, aoAlternar, salvando }) {
  if (!tema) return null;

  const travado = !tema.pode_alternar_fonte;
  const explicacao = travado
    ? `Travado no Google Doc pela configuração do servidor. Para liberar esta ` +
      `escolha, alguém com acesso à máquina precisa definir ` +
      `${tema.variavel_de_ambiente}=painel e reiniciar a API.`
    : 'Vale só para este macrotema; os outros sete seguem como estão.';

  return (
    <div className={`seletor-fonte${travado ? ' travado' : ''}`}>
      <span className="seletor-fonte-titulo">Relatório usa</span>
      <div className="seletor-fonte-opcoes" role="group" aria-label="Fonte do texto do relatório">
        {OPCOES.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            className={tema.fonte_editorial === opcao.valor ? 'ativa' : ''}
            aria-pressed={tema.fonte_editorial === opcao.valor}
            disabled={travado || salvando || tema.fonte_editorial === opcao.valor}
            title={explicacao}
            onClick={() => aoAlternar(opcao.valor)}
          >
            {opcao.rotulo}
          </button>
        ))}
      </div>
      <span className="seletor-fonte-nota">{salvando ? 'Salvando…' : explicacao}</span>
    </div>
  );
}
