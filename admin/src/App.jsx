import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, esquecerSessao, guardarSessao, lerSessao } from './api.js'
import Login from './components/Login.jsx'
import SeletorDeTema from './components/SeletorDeTema.jsx'
import ArvoreDeBlocos from './components/ArvoreDeBlocos.jsx'
import EditorDeBloco from './components/EditorDeBloco.jsx'
import PaletaDeVariaveis from './components/PaletaDeVariaveis.jsx'
import Previa from './components/Previa.jsx'
import EstadoDaConexao from './components/EstadoDaConexao.jsx'
import {
  atualizarBloco, blocoVazio, camposUsados, contarRegras, encontrarBloco,
  inserirBloco, moverBloco, removerBloco, todosOsBlocos,
} from './contrato.js'

export default function App() {
  const [sessao, setSessao] = useState(lerSessao);
  const [erroLogin, setErroLogin] = useState('');
  const [entrando, setEntrando] = useState(false);

  const [manifesto, setManifesto] = useState(null);
  const [temas, setTemas] = useState([]);
  const [cidades, setCidades] = useState([]);
  const [carregando, setCarregando] = useState(false);

  const [slug, setSlug] = useState(null);
  const [contrato, setContrato] = useState(null);
  const [versaoBase, setVersaoBase] = useState(null);
  const [sujo, setSujo] = useState(false);
  const [selecionado, setSelecionado] = useState(null);
  const [aba, setAba] = useState('editar');
  const [divergencias, setDivergencias] = useState(null);
  const [mensagem, setMensagem] = useState(null);
  const [publicando, setPublicando] = useState(false);

  const [cidade, setCidade] = useState('');
  const [previa, setPrevia] = useState(null);
  const [carregandoPrevia, setCarregandoPrevia] = useState(false);
  const [erroPrevia, setErroPrevia] = useState('');

  const editorAtivo = useRef(null);
  const token = sessao?.token;

  // Uma sessão expirada não pode deixar a tela num limbo: ao primeiro 401, o
  // painel volta para o login em vez de acumular erros.
  const tratarErro = useCallback((erro) => {
    if (erro?.status === 401) {
      esquecerSessao();
      setSessao(null);
      setErroLogin('Sessão expirada. Entre de novo.');
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelado = false;
    setCarregando(true);
    Promise.all([api.contratos(token), api.manifesto(), api.cidades()])
      .then(([listaTemas, manifestoNovo, listaCidades]) => {
        if (cancelado) return;
        setTemas(listaTemas);
        setManifesto(manifestoNovo);
        setCidades(Array.isArray(listaCidades) ? listaCidades : []);
      })
      .catch((erro) => {
        if (cancelado || tratarErro(erro)) return;
        setMensagem({ tipo: 'erro', texto: erro.message });
      })
      .finally(() => !cancelado && setCarregando(false));
    return () => { cancelado = true; };
  }, [token, tratarErro]);

  const entrar = async (nome, senha) => {
    setEntrando(true);
    setErroLogin('');
    try {
      const nova = await api.login(nome, senha);
      guardarSessao(nova);
      setSessao(nova);
    } catch (erro) {
      setErroLogin(erro.message);
    } finally {
      setEntrando(false);
    }
  };

  const sair = () => {
    if (sujo && !confirm('Há alterações não publicadas. Sair mesmo assim?')) return;
    esquecerSessao();
    setSessao(null);
    setSlug(null);
    setContrato(null);
    setSujo(false);
  };

  const abrirTema = async (novoSlug) => {
    try {
      const { contrato: lido } = await api.contrato(novoSlug, token);
      setSlug(novoSlug);
      setContrato(lido);
      setVersaoBase(lido.versao);
      setSujo(false);
      setSelecionado(lido.corpo?.blocos?.[0]?.id ?? null);
      setDivergencias(null);
      setMensagem(null);
      setPrevia(null);
      setAba('editar');
    } catch (erro) {
      if (!tratarErro(erro)) setMensagem({ tipo: 'erro', texto: erro.message });
    }
  };

  const voltar = () => {
    if (sujo && !confirm('Há alterações não publicadas. Voltar mesmo assim?')) return;
    setSlug(null);
    setContrato(null);
    setSujo(false);
  };

  const mudarContrato = (novo) => { setContrato(novo); setSujo(true); };

  const importar = async (baixar) => {
    const aviso = contrato && todosOsBlocos(contrato).length
      ? 'Importar substitui tudo o que está aberto aqui pelo conteúdo do Google Doc. Continuar?'
      : null;
    if (aviso && !confirm(aviso)) return;
    setCarregando(true);
    try {
      const resposta = await api.importar(slug, baixar, token);
      setContrato(resposta.contrato);
      setDivergencias(resposta.divergencias);
      setSujo(true);
      setSelecionado(resposta.contrato.corpo?.blocos?.[0]?.id ?? null);
      setMensagem({
        tipo: 'ok',
        texto: `Doc importado. ${resposta.divergencias.length} divergência(s) para revisar antes de publicar.`,
      });
    } catch (erro) {
      if (!tratarErro(erro)) setMensagem({ tipo: 'erro', texto: erro.message });
    } finally {
      setCarregando(false);
    }
  };

  const publicar = async () => {
    setPublicando(true);
    setMensagem(null);
    try {
      const publicado = await api.publicar(slug, contrato, versaoBase, token);
      setContrato(publicado);
      setVersaoBase(publicado.versao);
      setSujo(false);
      setTemas((atuais) =>
        atuais.map((t) =>
          t.slug === slug
            ? { ...t, contrato: { versao: publicado.versao, publicado_em: publicado.publicado_em, publicado_por: publicado.publicado_por } }
            : t
        )
      );
      setMensagem({ tipo: 'ok', texto: `Publicado na versão ${publicado.versao}.` });
    } catch (erro) {
      if (tratarErro(erro)) return;
      if (erro.status === 409) {
        setMensagem({
          tipo: 'conflito',
          texto: erro.detalhe?.mensagem || erro.message,
          versaoAtual: erro.detalhe?.versao_atual,
        });
      } else {
        setMensagem({ tipo: 'erro', texto: erro.message, erros: erro.detalhe?.erros });
      }
    } finally {
      setPublicando(false);
    }
  };

  const recarregarDoServidor = async () => {
    const { contrato: lido } = await api.contrato(slug, token);
    setContrato(lido);
    setVersaoBase(lido.versao);
    setSujo(false);
    setMensagem({ tipo: 'ok', texto: `Recarregado na versão ${lido.versao}. Reaplique sua alteração.` });
  };

  // Chamada pelo indicador de conexão: quando o túnel volta, a paleta precisa
  // trocar os campos do CSV pelos da view sem um reload que apagaria o rascunho.
  const recarregarManifesto = async () => {
    try {
      setManifesto(await api.manifesto());
    } catch (erro) {
      if (!tratarErro(erro)) setMensagem({ tipo: 'erro', texto: erro.message });
    }
  };

  const gerarPrevia = async () => {
    setCarregandoPrevia(true);
    setErroPrevia('');
    try {
      setPrevia(await api.previa(slug, contrato, cidade, token));
    } catch (erro) {
      if (!tratarErro(erro)) {
        setErroPrevia(
          Array.isArray(erro.detalhe?.erros)
            ? `${erro.message}: ${erro.detalhe.erros.join('; ')}`
            : erro.message
        );
      }
    } finally {
      setCarregandoPrevia(false);
    }
  };

  const infoCampos = manifesto?.campos?.[slug];
  const campos = infoCampos?.campos || [];
  const graficos = manifesto?.graficos?.[slug] || [];
  const rotuloDe = useCallback(
    (campo) => {
      const nome = campo.split('.').pop();
      return campos.find((c) => c.campo === nome)?.rotulo || nome;
    },
    [campos]
  );

  const blocoSelecionado = contrato && selecionado ? encontrarBloco(contrato, selecionado) : null;
  const usados = useMemo(() => (contrato ? camposUsados(contrato) : new Set()), [contrato]);
  const tema = temas.find((t) => t.slug === slug);

  if (!sessao) return <Login aoEntrar={entrar} erro={erroLogin} carregando={entrando} />;

  if (!slug) {
    return (
      <div className="app">
        <TopoDoPainel nome={sessao.nome} aoSair={sair} token={token} aoReconectar={recarregarManifesto} />
        {mensagem && <Faixa mensagem={mensagem} aoFechar={() => setMensagem(null)} />}
        <SeletorDeTema temas={temas} aoEscolher={abrirTema} carregando={carregando} />
      </div>
    );
  }

  return (
    <div className="app">
      <TopoDoPainel nome={sessao.nome} aoSair={sair} token={token} aoReconectar={recarregarManifesto} />

      <header className="barra-tema" style={{ '--cor-tema': tema?.cor || '#001A72' }}>
        <button type="button" className="link voltar" onClick={voltar}>← macrotemas</button>
        <h1>{tema?.nome || slug}</h1>
        <span className="versao">
          {versaoBase ? `versão ${versaoBase}` : 'ainda não publicado'}
          {sujo && <em className="sujo">alterações não publicadas</em>}
        </span>

        <nav className="abas">
          <button type="button" className={aba === 'editar' ? 'ativa' : ''} onClick={() => setAba('editar')}>Editar</button>
          <button type="button" className={aba === 'previa' ? 'ativa' : ''} onClick={() => setAba('previa')}>Prévia</button>
          {divergencias?.length > 0 && (
            <button type="button" className={aba === 'divergencias' ? 'ativa' : ''} onClick={() => setAba('divergencias')}>
              Divergências <span className="contagem">{divergencias.length}</span>
            </button>
          )}
        </nav>

        <div className="acoes-tema">
          {tema?.tem_doc && (
            <>
              <button type="button" className="secundario" onClick={() => importar(false)}>
                Importar do Doc (cópia local)
              </button>
              <button type="button" className="secundario" onClick={() => importar(true)}>
                Baixar do Google Docs
              </button>
            </>
          )}
          <button type="button" onClick={publicar} disabled={publicando || !sujo}>
            {publicando ? 'Publicando…' : 'Publicar'}
          </button>
        </div>
      </header>

      {tema?.fonte_editorial === 'docs' && (
        <p className="faixa-info">
          Os relatórios de <strong>{tema.nome}</strong> ainda são gerados pelo Google Doc.
          Publicar aqui <strong>não muda</strong> o que sai em produção — para isso, ligue
          <code> FONTE_EDITORIAL_{slug.toUpperCase().replaceAll('-', '_')}=painel</code>.
        </p>
      )}

      {mensagem && (
        <Faixa
          mensagem={mensagem}
          aoFechar={() => setMensagem(null)}
          aoRecarregar={mensagem.tipo === 'conflito' ? recarregarDoServidor : null}
        />
      )}

      {aba === 'editar' && (
        <main className="area-edicao">
          <ArvoreDeBlocos
            contrato={contrato}
            selecionado={selecionado}
            aoSelecionar={setSelecionado}
            aoMover={(id, passo) => mudarContrato(moverBloco(contrato, id, passo))}
            aoRemover={(id) => {
              if (!confirm('Remover este bloco?')) return;
              mudarContrato(removerBloco(contrato, id));
              if (selecionado === id) setSelecionado(null);
            }}
            aoAdicionar={(destino) => {
              const bloco = blocoVazio(contrato, 'paragrafo');
              mudarContrato(inserirBloco(contrato, destino, bloco));
              setSelecionado(bloco.id);
            }}
            aoAdicionarFilho={(paiId) => {
              const bloco = blocoVazio(contrato, 'paragrafo');
              mudarContrato(inserirBloco(contrato, { paiId }, bloco));
              setSelecionado(bloco.id);
            }}
          />

          <section className="painel-central">
            {blocoSelecionado && (
              <TrocadorDeTipo
                bloco={blocoSelecionado}
                aoTrocar={(tipo) => {
                  const molde = blocoVazio(contrato, tipo);
                  mudarContrato(
                    atualizarBloco(contrato, blocoSelecionado.id, {
                      ...molde,
                      id: blocoSelecionado.id,
                      regra: blocoSelecionado.regra,
                    })
                  );
                }}
              />
            )}
            <EditorDeBloco
              bloco={blocoSelecionado}
              campos={campos}
              graficos={graficos}
              manifesto={manifesto}
              rotuloDe={rotuloDe}
              registrarEditor={(instancia) => { editorAtivo.current = instancia; }}
              aoMudar={(novo) => mudarContrato(atualizarBloco(contrato, novo.id, novo))}
            />
          </section>

          <PaletaDeVariaveis
            campos={campos}
            graficos={graficos}
            origem={infoCampos?.origem}
            aviso={infoCampos?.aviso}
            usados={usados}
            aoInserir={(campo) => {
              if (!editorAtivo.current) {
                setMensagem({ tipo: 'erro', texto: 'Clique antes no texto onde a variável deve entrar.' });
                return;
              }
              editorAtivo.current.inserirVariavel(campo.campo, campo.rotulo);
            }}
            aoInserirGrafico={(grafico) => {
              const bloco = { ...blocoVazio(contrato, 'grafico'), grafico: grafico.nome };
              mudarContrato(inserirBloco(contrato, { slot: 'corpo', depoisDe: selecionado }, bloco));
              setSelecionado(bloco.id);
            }}
          />
        </main>
      )}

      {aba === 'previa' && (
        <Previa
          cidades={cidades}
          cidade={cidade}
          aoTrocarCidade={setCidade}
          resultado={previa}
          carregando={carregandoPrevia}
          erro={erroPrevia}
          aoGerar={gerarPrevia}
        />
      )}

      {aba === 'divergencias' && <Divergencias itens={divergencias} />}

      <footer className="rodape">
        {contrato && (
          <>
            {todosOsBlocos(contrato).length} blocos · {contarRegras(contrato)} com regra ·
            {' '}{usados.size} variáveis em uso
          </>
        )}
      </footer>
    </div>
  );
}

function TopoDoPainel({ nome, aoSair, token, aoReconectar }) {
  return (
    <div className="topo">
      <span className="marca">Data Nordeste · Painel Editorial</span>
      <span className="usuario">
        <EstadoDaConexao token={token} api={api} aoReconectar={aoReconectar} />
        {nome}
        <button type="button" className="link" onClick={aoSair}>sair</button>
      </span>
    </div>
  );
}

function Faixa({ mensagem, aoFechar, aoRecarregar }) {
  return (
    <div className={`faixa ${mensagem.tipo}`}>
      <div>
        <p>{mensagem.texto}</p>
        {mensagem.erros?.length > 0 && (
          <ul>{mensagem.erros.map((erro) => <li key={erro}>{erro}</li>)}</ul>
        )}
      </div>
      <span className="faixa-acoes">
        {aoRecarregar && (
          <button type="button" className="secundario" onClick={aoRecarregar}>
            Recarregar a versão publicada
          </button>
        )}
        <button type="button" className="icone" onClick={aoFechar} aria-label="Fechar">×</button>
      </span>
    </div>
  );
}

function TrocadorDeTipo({ bloco, aoTrocar }) {
  return (
    <div className="trocador-tipo">
      <span>Tipo</span>
      <select value={bloco.tipo} onChange={(e) => aoTrocar(e.target.value)}>
        <option value="paragrafo">Parágrafo</option>
        <option value="secao">Seção</option>
        <option value="lista">Lista</option>
        <option value="grafico">Gráfico</option>
        <option value="legenda">Legenda de figura</option>
        <option value="caixa">Caixa destacada</option>
        <option value="nota">Nota</option>
      </select>
      <small>Trocar o tipo mantém a regra, mas o conteúdo começa do zero.</small>
    </div>
  );
}

function Divergencias({ itens }) {
  const porTipo = itens.reduce((acumulado, item) => {
    (acumulado[item.tipo] = acumulado[item.tipo] || []).push(item);
    return acumulado;
  }, {});

  return (
    <section className="divergencias">
      <header>
        <h2>O que muda em relação ao Google Doc</h2>
        <p>
          Cada item é um ponto em que o contrato <strong>não</strong> reproduz o
          comportamento atual. Divergência prevista não é erro — é o que precisa ser
          conferido antes de publicar.
        </p>
      </header>
      {Object.entries(porTipo).map(([tipo, lista]) => (
        <article key={tipo}>
          <h3>{tipo} <span className="contagem">{lista.length}</span></h3>
          {lista.map((item, i) => (
            <div className="divergencia" key={`${tipo}-${i}`}>
              <p className="trecho"><code>{item.trecho}</code> <span className="linha">linha {item.linha}</span></p>
              <p><b>Hoje:</b> {item.legado}</p>
              <p><b>Contrato:</b> {item.contrato}</p>
              {item.prova && <p className="prova"><b>Prova:</b> {item.prova}</p>}
            </div>
          ))}
        </article>
      ))}
    </section>
  );
}
