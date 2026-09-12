import React, { useState } from 'react'

// O painel carrega a lista de variáveis uma vez, quando a aba abre. Se o túnel
// SSH subir depois disso, a tela continua mostrando os campos da planilha CSV e
// parece quebrada — mesmo com o backend já enxergando o banco. Este componente
// existe para reconferir sem recarregar a página, o que faria o editor perder o
// texto que ainda não publicou.
//
// Abrir o túnel continua sendo trabalho de um terminal: a chave pede
// passphrase, e só uma pessoa consegue digitá-la. O que dá para fazer aqui é
// entregar o comando certo, já com o host e a porta que esta instalação usa.

export default function EstadoDaConexao({ token, api, aoReconectar }) {
  const [estado, setEstado] = useState(null);
  const [testando, setTestando] = useState(false);
  const [aberto, setAberto] = useState(false);
  const [copiado, setCopiado] = useState(false);

  const testar = async () => {
    setTestando(true);
    try {
      const novo = await api.conexao(token);
      setEstado(novo);
      setAberto(!novo.conectado);
      // Reconectou: recarrega o manifesto para a paleta trocar os campos do
      // CSV pelos da view sem passar por um reload da página.
      if (novo.conectado) await aoReconectar();
    } catch (erro) {
      setEstado({ conectado: false, detalhe: erro.message });
      setAberto(true);
    } finally {
      setTestando(false);
    }
  };

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(estado.comando_tunel);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setCopiado(false);
    }
  };

  const classe = estado === null ? 'indefinido' : estado.conectado ? 'ligado' : 'desligado';
  const rotulo =
    estado === null ? 'Conexão não testada'
      : estado.conectado ? 'Banco conectado'
        : 'Banco sem conexão';

  return (
    <div className="conexao">
      <button
        type="button"
        className={`selo-conexao ${classe}`}
        onClick={testar}
        disabled={testando}
        title={estado?.detalhe || 'Clique para testar a conexão com o banco'}
      >
        <span className="bolinha" aria-hidden="true" />
        {testando ? 'Testando…' : rotulo}
      </button>

      {estado && !estado.conectado && aberto && (
        <div className="conexao-ajuda" role="status">
          <p className="conexao-erro">{estado.detalhe}</p>
          <p>
            O banco do Data Nordeste roda na VM e só chega até aqui pelo túnel SSH.
            Abra num terminal à parte — ele pede a passphrase da chave e fica aberto:
          </p>
          <pre>{estado.comando_tunel}</pre>
          <div className="conexao-acoes">
            <button type="button" className="secundario" onClick={copiar}>
              {copiado ? 'Copiado' : 'Copiar comando'}
            </button>
            <button type="button" onClick={testar} disabled={testando}>
              Testar de novo
            </button>
            <button type="button" className="link" onClick={() => setAberto(false)}>
              fechar
            </button>
          </div>
          <p className="conexao-nota">
            Fora do escritório, conecte a VPN antes. Confira com{' '}
            <code>python3 -m utils.database</code> até sair “Conexão bem-sucedida!”.
          </p>
        </div>
      )}
    </div>
  );
}
