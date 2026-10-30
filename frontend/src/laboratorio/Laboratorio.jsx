import React, { useEffect, useMemo, useRef, useState } from 'react'
import { agruparEmBlocos, condicaoDoItem, exportar, lerDoc, textoDoItem } from './modelo.js'

// Mesma origem quando servido pela API; no dev do Vite, VITE_API_BASE_URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL || window.location.origin
const INTERVALO_MS = 1000
const MAX_NOMES = 8

async function pedir(caminho, opcoes) {
  const resposta = await fetch(`${API_BASE}${caminho}`, opcoes)
  const corpo = await resposta.json().catch(() => ({}))
  if (!resposta.ok) throw Object.assign(new Error(corpo.detail || `Erro ${resposta.status}`), { status: resposta.status })
  return corpo
}

const postarJson = (caminho, corpo) =>
  pedir(caminho, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) })

const dataHora = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
const numero = (n) => n.toLocaleString('pt-BR')
const municipios = (n) => `${numero(n)} ${n === 1 ? 'município' : 'municípios'}`

// Só para a tela: várias linhas em branco seguidas viram uma. A exportação usa o original.
const paraTela = (texto) => texto.trim().replace(/\n\s*\n(\s*\n)+/g, '\n\n')

function Nomes({ nomes, total }) {
  if (!nomes.length) return null
  const resto = total - nomes.length
  return <span className="nomes">{nomes.join(', ')}{resto > 0 ? ` e mais ${numero(resto)}` : ''}</span>
}

// Contagens de um bloco: municípios em nenhuma versão e em duas ou mais.
function estatisticasDoBloco(posicoes, versoesPorMunicipio) {
  const doBloco = new Set(posicoes)
  const sem = []
  const varias = []
  for (const [cidade, disparadas] of Object.entries(versoesPorMunicipio)) {
    const n = disparadas.filter((k) => doBloco.has(k)).length
    if (n === 0) sem.push(cidade)
    else if (n > 1) varias.push(cidade)
  }
  return { sem, varias }
}

// O textarea mostra o miolo; o espaço em volta (linhas em branco do Doc) volta igual.
function separarEspacos(texto) {
  const [, antes, miolo, depois] = texto.match(/^(\s*)([\s\S]*?)(\s*)$/)
  return { antes, miolo, depois }
}

function Versao({ item, contagem, naCidade, podeSeparar, acoes }) {
  const texto = textoDoItem(item)
  // Versão recém-criada já abre em edição, com o modelo no textarea.
  const [editando, setEditando] = useState(item.original === '' && item.editado !== undefined)
  const [rascunho, setRascunho] = useState(() => separarEspacos(texto).miolo)
  const condicao = condicaoDoItem(item)
  const removida = texto === ''
  const estado = item.original === '' ? 'nova' : removida ? 'removida' : item.editado !== undefined ? 'alterada' : null

  function abrirEdicao() {
    setRascunho(separarEspacos(texto).miolo)
    setEditando(true)
  }
  function salvar() {
    const { antes, depois } = separarEspacos(texto)
    acoes.salvar(antes + rascunho.trim() + (depois || '\n'))
    setEditando(false)
  }

  if (editando) {
    return (
      <div className="versao editando">
        <textarea value={rascunho} onChange={(e) => setRascunho(e.target.value)} rows={Math.max(4, rascunho.split('\n').length + 1)} autoFocus />
        <div className="acoes">
          <button className="btn pri sm" onClick={salvar}>Pronto</button>
          <button className="btn sm" onClick={() => (item.original === '' && !item.editado.trim() ? acoes.desfazer() : setEditando(false))}>Cancelar</button>
        </div>
      </div>
    )
  }

  const classe = removida ? ' removida' : naCidade === undefined ? '' : naCidade ? ' dispara' : ' apagada'
  const corpo = separarEspacos(texto).miolo.split('\n').slice(1).join('\n')
  return (
    <div className={`versao${classe}`}>
      <div className="linha-condicao">
        <span className={`condicao${condicao || removida ? '' : ' quebrada'}`}>
          {removida ? item.condicao : condicao ?? 'A 1ª linha não é mais uma condição: o gerador vai ler isto como texto fixo'}
        </span>
        {estado && <span className={`chip ${estado === 'removida' ? 'ruim' : 'atencao'}`}>{estado}</span>}
        {contagem !== undefined && !removida && (
          <span className={`chip ${contagem ? '' : 'ruim'}`}>
            {contagem ? `aparece em ${municipios(contagem)}` : 'não aparece em nenhum município'}
          </span>
        )}
        {naCidade && !removida && <span className="chip bom">vale nesta cidade</span>}
        <span className="spacer" />
        {estado && <button className="btn ghost sm" onClick={acoes.desfazer}>desfazer</button>}
        {!removida && <button className="btn ghost sm" onClick={abrirEdicao}>editar</button>}
        {!removida && podeSeparar && <button className="btn ghost sm" onClick={acoes.separar} title="Esta versão e as de baixo passam a ser outro bloco">separar daqui</button>}
        {!removida && <button className="btn ghost sm" onClick={acoes.remover}>remover</button>}
      </div>
      {!removida && <div className="corpo">{paraTela(corpo)}</div>}
    </div>
  )
}

function Texto({ item }) {
  return <div className="card texto"><div className="cbody">{paraTela(textoDoItem(item))}</div></div>
}

function Bloco({ numero: n, versoes, estatisticas, juntar, novaVersao }) {
  return (
    <div className="card">
      <div className="chead">
        <span className="ctag">Bloco {n}</span>
        <span className="muted">{versoes.length} {versoes.length === 1 ? 'versão' : 'versões'}</span>
        {estatisticas && (
          <>
            <span className={`chip ${estatisticas.sem.length ? 'atencao' : 'bom'}`}>
              fica de fora em {municipios(estatisticas.sem.length)}
            </span>
            <span className={`chip ${estatisticas.varias.length ? 'ruim' : 'bom'}`}>
              sai com 2+ trechos em {municipios(estatisticas.varias.length)}
            </span>
          </>
        )}
        <span className="spacer" />
        {juntar && <button className="btn ghost sm" onClick={juntar}>juntar com o de cima</button>}
      </div>
      {estatisticas && (estatisticas.sem.length > 0 || estatisticas.varias.length > 0) && (
        <div className="bloco-detalhe">
          {estatisticas.varias.length > 0 && (
            <div>
              <b>Sai com 2+ trechos em:</b> <Nomes nomes={estatisticas.varias.slice(0, MAX_NOMES)} total={estatisticas.varias.length} />
              <div className="muted">Se são parágrafos seguidos que devem sair juntos, não é erro: use "separar daqui" na versão que começa o outro assunto.</div>
            </div>
          )}
          {estatisticas.sem.length > 0 && (
            <div><b>Fica de fora em:</b> <Nomes nomes={estatisticas.sem.slice(0, MAX_NOMES)} total={estatisticas.sem.length} /></div>
          )}
        </div>
      )}
      <div className="cbody">
        {versoes}
        <button className="btn ghost sm nova" onClick={novaVersao}>+ nova versão</button>
      </div>
    </div>
  )
}

function Avisos({ resultado }) {
  const avisos = []
  for (const campo of resultado.campos_crus) {
    avisos.push(
      <div key={`c-${campo.campo}`} className={`banner ${campo.existe ? 'atencao' : 'erro'}`}>
        <b>${campo.campo}</b>{' '}
        {campo.existe
          ? `existe, mas está vazio em ${municipios(campo.municipios.length)} e sai cru no texto: `
          : 'não existe nos dados de nenhum município e sai cru no texto. '}
        {campo.existe && <Nomes nomes={campo.municipios.slice(0, MAX_NOMES)} total={campo.municipios.length} />}
      </div>
    )
  }
  for (const aviso of resultado.condicoes_nao_entendidas) {
    avisos.push(<div key={`n-${aviso}`} className="banner erro"><b>O gerador não entende esta condição:</b> {aviso}</div>)
  }
  for (const condicao of resultado.condicoes_sem_efeito) {
    avisos.push(
      <div key={`s-${condicao}`} className="banner erro">
        <b>Condição no resumo do tema</b> ({condicao}): o resumo não interpreta condições, ela sairia escrita no relatório.
      </div>
    )
  }
  for (const grafico of resultado.graficos_sem_legenda) {
    avisos.push(<div key={`g-${grafico}`} className="banner atencao"><b>Gráfico sem legenda no Doc:</b> {grafico} (sem "Figura N – …", ele não entra).</div>)
  }
  const erros = Object.entries(resultado.erros)
  if (erros.length) {
    avisos.push(<div key="erros" className="banner erro"><b>Erro em {municipios(erros.length)}:</b> {erros.slice(0, 3).map(([c, e]) => `${c} (${e})`).join('; ')}</div>)
  }
  return avisos
}

export default function Laboratorio() {
  const [temas, setTemas] = useState(null)
  const [desligado, setDesligado] = useState(false)
  const [tema, setTema] = useState('')
  const [doc, setDoc] = useState(null)
  const [itens, setItens] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [conferencia, setConferencia] = useState(null)
  const [cidades, setCidades] = useState([])
  const [cidade, setCidade] = useState('')
  const [naCidade, setNaCidade] = useState(null)
  const [ajustes, setAjustes] = useState({ cortes: new Set(), juncoes: new Set() })
  const [textoConferido, setTextoConferido] = useState(null)
  const temaVivo = useRef('')
  const proximoId = useRef(0)

  useEffect(() => {
    pedir('/laboratorio/temas')
      .then((lista) => {
        setTemas(lista)
        // ?tema=<slug> abre direto: dá para mandar o link de um tema para alguém.
        const doLink = new URLSearchParams(window.location.search).get('tema')
        if (lista.some((t) => t.slug === doLink && t.snapshot_gerado_em)) abrirTema(doLink)
      })
      .catch((err) => (err.status === 404 ? setDesligado(true) : setErro(err.message)))
    pedir('/cities').then(setCidades).catch(() => {})
  }, [])

  async function abrirTema(slug) {
    temaVivo.current = slug
    setTema(slug)
    setDoc(null)
    setItens([])
    setErro('')
    setConferencia(null)
    setNaCidade(null)
    setAjustes({ cortes: new Set(), juncoes: new Set() })
    if (!slug) return
    setCarregando(true)
    try {
      const aberto = await pedir(`/laboratorio/${slug}/doc`)
      setDoc({ ...aberto, aberto_em: new Date().toISOString() })
      const lidos = lerDoc(aberto.texto)
      proximoId.current = lidos.length
      setItens(lidos)
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }

  async function conferir() {
    const slug = tema
    setErro('')
    setConferencia({ estado: 'na_fila' })
    const texto = exportar(itens)
    setTextoConferido(texto)
    try {
      const { id } = await postarJson(`/laboratorio/${slug}/conferencias`, { texto })
      for (;;) {
        await new Promise((r) => setTimeout(r, INTERVALO_MS))
        if (temaVivo.current !== slug) return // trocou de tema no meio
        const estado = await pedir(`/laboratorio/conferencias/${id}`)
        setConferencia({ ...estado, conferido_em: new Date().toISOString() })
        if (estado.estado === 'pronta' || estado.estado === 'erro') return
      }
    } catch (err) {
      setConferencia(null)
      setErro(err.message)
    }
  }

  async function escolherCidade(nome, comItens = itens) {
    setCidade(nome)
    setNaCidade(null)
    if (!tema || !cidades.includes(nome)) return
    try {
      setNaCidade({ cidade: nome, ...(await postarJson(`/laboratorio/${tema}/municipio`, { texto: exportar(comItens), cidade: nome })) })
    } catch (err) {
      setErro(err.message)
    }
  }

  // Toda mudança no texto passa por aqui: o "ver numa cidade" acompanha na hora (1
  // chamada); a conferência inteira, não (~25 s), e a tela avisa que ficou velha.
  function mudarItens(novos) {
    setItens(novos)
    if (naCidade) escolherCidade(cidade, novos)
  }
  const acoesDaVersao = (id) => ({
    salvar: (texto) =>
      mudarItens(itens.map((i) => (i.id !== id ? i : texto === i.original ? { ...i, editado: undefined } : { ...i, editado: texto }))),
    remover: () => mudarItens(itens.map((i) => (i.id === id ? { ...i, editado: '' } : i))),
    desfazer: () =>
      mudarItens(itens.flatMap((i) => (i.id !== id ? [i] : i.original === '' ? [] : [{ ...i, editado: undefined }]))),
    separar: () =>
      setAjustes(({ cortes, juncoes }) => ({ cortes: new Set(cortes).add(id), juncoes: new Set([...juncoes].filter((j) => j !== id)) })),
  })
  function juntarComOdeCima(id) {
    setAjustes(({ cortes, juncoes }) => ({ cortes: new Set([...cortes].filter((c) => c !== id)), juncoes: new Set(juncoes).add(id) }))
  }
  function novaVersao(depoisDoId) {
    const prefixo = tema.split('-')[0]
    const nova = {
      id: proximoId.current++,
      tipo: 'versao',
      original: '',
      editado: `\nPara quando ${prefixo}.$campo for igual a 0, então:\nTexto desta versão.\n`,
      condicao: null,
    }
    const posicaoNoTexto = itens.findIndex((i) => i.id === depoisDoId) + 1
    // Fica no bloco onde foi criada, mesmo antes de a editora trocar o $campo do modelo.
    setAjustes(({ cortes, juncoes }) => ({ cortes, juncoes: new Set(juncoes).add(nova.id) }))
    mudarItens([...itens.slice(0, posicaoNoTexto), nova, ...itens.slice(posicaoNoTexto)])
  }

  const grupos = useMemo(() => agruparEmBlocos(itens, ajustes), [itens, ajustes])
  // Posição de cada versão (que ainda é condição) na ordem do texto: é assim que o
  // backend devolve as contagens.
  const posicao = useMemo(() => {
    const mapa = new Map()
    itens.forEach((item, indice) => item.tipo === 'versao' && condicaoDoItem(item) && mapa.set(indice, mapa.size))
    return mapa
  }, [itens])

  const resultado = conferencia?.estado === 'pronta' ? conferencia.resultado : null
  const casaComOTexto =
    resultado &&
    resultado.versoes.length === posicao.size &&
    [...posicao].every(([indice, k]) => resultado.versoes[k].condicao === condicaoDoItem(itens[indice]))
  const conferenciaVelha = resultado && textoConferido !== exportar(itens)
  const temaAtual = temas?.find((t) => t.slug === tema)
  let numeroBloco = 0

  if (desligado) {
    return (
      <main>
        <div className="empty">
          <h2>O laboratório não está ligado neste ambiente</h2>
          <p>Ele só funciona onde a API roda com LABORATORIO_HABILITADO=1 (o gamma).</p>
        </div>
      </main>
    )
  }

  const rodando = conferencia && (conferencia.estado === 'na_fila' || conferencia.estado === 'rodando')

  return (
    <>
      <header>
        <div className="hrow">
          <h1>Laboratório de Temas</h1>
          <select value={tema} onChange={(e) => abrirTema(e.target.value)} disabled={!temas || carregando || rodando}>
            <option value="">Escolha o tema</option>
            {temas?.map((t) => (
              <option key={t.slug} value={t.slug} disabled={!t.snapshot_gerado_em}>
                {t.nome}{t.snapshot_gerado_em ? '' : ' (sem dados ainda)'}
              </option>
            ))}
          </select>
          <button className="btn pri" onClick={conferir} disabled={!doc || rodando}>Conferir</button>
          <input
            className="cidade"
            list="cidades"
            placeholder="Ver numa cidade…"
            value={cidade}
            onChange={(e) => escolherCidade(e.target.value)}
            disabled={!doc}
          />
          <datalist id="cidades">{cidades.map((c) => <option key={c} value={c} />)}</datalist>
          <span className="spacer" />
          {doc && (
            <span className="status">
              Doc aberto às <b>{dataHora(doc.aberto_em)}</b> · dados de <b>{dataHora(temaAtual.snapshot_gerado_em)}</b>
            </span>
          )}
        </div>
        {rodando && (
          <div className="progresso">
            <div className="barra" style={{ width: `${conferencia.total ? (100 * conferencia.feitos) / conferencia.total : 0}%` }} />
            <span>
              {conferencia.estado === 'na_fila'
                ? 'Na fila: outra conferência está rodando…'
                : `Conferindo ${numero(conferencia.feitos)} de ${numero(conferencia.total)} municípios…`}
            </span>
          </div>
        )}
      </header>
      <main>
        {erro && <div className="banner erro">{erro}</div>}
        {conferencia?.estado === 'erro' && <div className="banner erro">A conferência falhou: {conferencia.erro}</div>}
        {resultado && (
          <div className="resumo">
            Conferido às <b>{dataHora(conferencia.conferido_em)}</b> contra {municipios(conferencia.total)}.{' '}
            {resultado.versoes.filter((v) => !v.municipios).length} versões não aparecem em nenhum município.
          </div>
        )}
        {conferenciaVelha && (
          <div className="banner atencao">O texto mudou desde a conferência: os números abaixo são do texto anterior. Clique em Conferir de novo.</div>
        )}
        {resultado && !casaComOTexto && !conferenciaVelha && (
          <div className="banner atencao">As versões do texto não batem com as da conferência. Confira de novo.</div>
        )}
        {resultado && <Avisos resultado={resultado} />}
        {naCidade && (
          <details className="card cidade-texto" open>
            <summary className="chead"><span className="ctag">Texto pronto</span> {naCidade.cidade}</summary>
            <div className="cbody">{naCidade.partes.join('\n\n')}</div>
          </details>
        )}
        {carregando && <div className="empty"><p>Abrindo o Doc…</p></div>}
        {!tema && !carregando && (
          <div className="empty">
            <h2>Escolha um tema</h2>
            <p>O laboratório abre a versão mais recente do Doc e confere o texto contra os 2.074 municípios, pelo mesmo código do relatório.</p>
          </div>
        )}
        {grupos.map((grupo, i) => {
          // Chaves com prefixo: id de texto e id de versão são números da mesma sequência,
          // e "b-3" e "t-3" não podem colidir (o React reaproveitaria o cartão errado).
          if (grupo.tipo !== 'bloco') return <Texto key={`t-${itens[grupo.indice].id}`} item={itens[grupo.indice]} />
          const posicoes = grupo.versoes.map((indice) => posicao.get(indice)).filter((k) => k !== undefined)
          const contaCom = casaComOTexto && !conferenciaVelha
          const primeiro = itens[grupo.versoes[0]]
          return (
            <Bloco
              key={`b-${primeiro.id}`}
              numero={++numeroBloco}
              estatisticas={contaCom ? estatisticasDoBloco(posicoes, resultado.versoes_por_municipio) : null}
              juntar={grupos[i - 1]?.tipo === 'bloco' ? () => juntarComOdeCima(primeiro.id) : null}
              novaVersao={() => novaVersao(itens[grupo.versoes.at(-1)].id)}
              versoes={grupo.versoes.map((indice, j) => {
                const k = posicao.get(indice)
                return (
                  <Versao
                    key={itens[indice].id}
                    item={itens[indice]}
                    contagem={contaCom && k !== undefined ? resultado.versoes[k].municipios : undefined}
                    naCidade={naCidade && k !== undefined ? naCidade.versoes[k]?.[1] : undefined}
                    podeSeparar={j > 0}
                    acoes={acoesDaVersao(itens[indice].id)}
                  />
                )
              })}
            />
          )
        })}
      </main>
    </>
  )
}
