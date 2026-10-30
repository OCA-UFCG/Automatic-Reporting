import React, { useEffect, useMemo, useRef, useState } from 'react'
import { agruparEmBlocos, exportar, lerDoc } from './modelo.js'

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

function Versao({ item, contagem, naCidade }) {
  const corpo = item.original.split('\n').slice(1).join('\n')
  const classe = naCidade === undefined ? '' : naCidade ? ' dispara' : ' apagada'
  return (
    <div className={`versao${classe}`}>
      <div className="linha-condicao">
        <span className="condicao">{item.condicao}</span>
        {contagem !== undefined && (
          <span className={`chip ${contagem ? '' : 'ruim'}`}>
            {contagem ? `aparece em ${municipios(contagem)}` : 'não aparece em nenhum município'}
          </span>
        )}
        {naCidade && <span className="chip bom">vale nesta cidade</span>}
      </div>
      <div className="corpo">{paraTela(corpo)}</div>
    </div>
  )
}

function Texto({ item }) {
  return <div className="card texto"><div className="cbody">{paraTela(item.original)}</div></div>
}

function Bloco({ numero: n, versoes, estatisticas }) {
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
      </div>
      {estatisticas && (estatisticas.sem.length > 0 || estatisticas.varias.length > 0) && (
        <div className="bloco-detalhe">
          {estatisticas.varias.length > 0 && (
            <div><b>Sai com 2+ trechos em:</b> <Nomes nomes={estatisticas.varias.slice(0, MAX_NOMES)} total={estatisticas.varias.length} /></div>
          )}
          {estatisticas.sem.length > 0 && (
            <div><b>Fica de fora em:</b> <Nomes nomes={estatisticas.sem.slice(0, MAX_NOMES)} total={estatisticas.sem.length} /></div>
          )}
        </div>
      )}
      <div className="cbody">{versoes}</div>
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
  const temaVivo = useRef('')

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
    if (!slug) return
    setCarregando(true)
    try {
      const aberto = await pedir(`/laboratorio/${slug}/doc`)
      setDoc({ ...aberto, aberto_em: new Date().toISOString() })
      setItens(lerDoc(aberto.texto))
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
    try {
      const { id } = await postarJson(`/laboratorio/${slug}/conferencias`, { texto: exportar(itens) })
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

  async function escolherCidade(nome) {
    setCidade(nome)
    setNaCidade(null)
    if (!tema || !cidades.includes(nome)) return
    try {
      setNaCidade({ cidade: nome, ...(await postarJson(`/laboratorio/${tema}/municipio`, { texto: exportar(itens), cidade: nome })) })
    } catch (err) {
      setErro(err.message)
    }
  }

  const grupos = useMemo(() => agruparEmBlocos(itens), [itens])
  // Posição de cada versão na ordem do texto: é assim que o backend devolve as contagens.
  const posicao = useMemo(() => {
    const mapa = new Map()
    itens.forEach((item, indice) => item.tipo === 'versao' && mapa.set(indice, mapa.size))
    return mapa
  }, [itens])

  const resultado = conferencia?.estado === 'pronta' ? conferencia.resultado : null
  const casaComOTexto =
    resultado &&
    resultado.versoes.length === posicao.size &&
    [...posicao].every(([indice, k]) => resultado.versoes[k].condicao === itens[indice].condicao)
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
        {resultado && !casaComOTexto && (
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
          if (grupo.tipo !== 'bloco') return <Texto key={i} item={itens[grupo.indice]} />
          const posicoes = grupo.versoes.map((indice) => posicao.get(indice))
          return (
            <Bloco
              key={i}
              numero={++numeroBloco}
              estatisticas={casaComOTexto ? estatisticasDoBloco(posicoes, resultado.versoes_por_municipio) : null}
              versoes={grupo.versoes.map((indice, j) => (
                <Versao
                  key={indice}
                  item={itens[indice]}
                  contagem={casaComOTexto ? resultado.versoes[posicoes[j]].municipios : undefined}
                  naCidade={naCidade ? naCidade.versoes[posicoes[j]]?.[1] : undefined}
                />
              ))}
            />
          )
        })}
      </main>
    </>
  )
}
