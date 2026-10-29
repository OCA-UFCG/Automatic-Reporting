import React, { useEffect, useMemo, useState } from 'react'
import { agruparEmBlocos, lerDoc } from './modelo.js'

// Mesma origem quando servido pela API; no dev do Vite, VITE_API_BASE_URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL || window.location.origin

async function pedir(caminho, opcoes) {
  const resposta = await fetch(`${API_BASE}${caminho}`, opcoes)
  const corpo = await resposta.json().catch(() => ({}))
  if (!resposta.ok) throw Object.assign(new Error(corpo.detail || `Erro ${resposta.status}`), { status: resposta.status })
  return corpo
}

const dataHora = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

// Só para a tela: várias linhas em branco seguidas viram uma. A exportação usa o original.
const paraTela = (texto) => texto.trim().replace(/\n\s*\n(\s*\n)+/g, '\n\n')

function Versao({ item }) {
  const corpo = item.original.split('\n').slice(1).join('\n')
  return (
    <div className="versao">
      <div className="condicao">{item.condicao}</div>
      <div className="corpo">{paraTela(corpo)}</div>
    </div>
  )
}

function Texto({ item }) {
  return <div className="card texto"><div className="cbody">{paraTela(item.original)}</div></div>
}

function Bloco({ numero, versoes }) {
  return (
    <div className="card">
      <div className="chead">
        <span className="ctag">Bloco {numero}</span>
        <span className="muted">{versoes.length} {versoes.length === 1 ? 'versão' : 'versões'}</span>
      </div>
      <div className="cbody">{versoes.map((item, i) => <Versao key={i} item={item} />)}</div>
    </div>
  )
}

export default function Laboratorio() {
  const [temas, setTemas] = useState(null)
  const [desligado, setDesligado] = useState(false)
  const [tema, setTema] = useState('')
  const [doc, setDoc] = useState(null)
  const [itens, setItens] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => {
    pedir('/laboratorio/temas')
      .then((lista) => {
        setTemas(lista)
        // ?tema=<slug> abre direto: dá para mandar o link de um tema para alguém.
        const doLink = new URLSearchParams(window.location.search).get('tema')
        if (lista.some((t) => t.slug === doLink && t.snapshot_gerado_em)) abrirTema(doLink)
      })
      .catch((err) => (err.status === 404 ? setDesligado(true) : setErro(err.message)))
  }, [])

  async function abrirTema(slug) {
    setTema(slug)
    setDoc(null)
    setItens([])
    setErro('')
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

  const grupos = useMemo(() => agruparEmBlocos(itens), [itens])
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

  return (
    <>
      <header>
        <div className="hrow">
          <h1>Laboratório de Temas</h1>
          <select value={tema} onChange={(e) => abrirTema(e.target.value)} disabled={!temas || carregando}>
            <option value="">Escolha o tema</option>
            {temas?.map((t) => (
              <option key={t.slug} value={t.slug} disabled={!t.snapshot_gerado_em}>
                {t.nome}{t.snapshot_gerado_em ? '' : ' (sem dados ainda)'}
              </option>
            ))}
          </select>
          <span className="spacer" />
          {doc && (
            <span className="status">
              Doc aberto às <b>{dataHora(doc.aberto_em)}</b> · dados de <b>{dataHora(temaAtual.snapshot_gerado_em)}</b>
            </span>
          )}
        </div>
      </header>
      <main>
        {erro && <div className="banner erro">{erro}</div>}
        {carregando && <div className="empty"><p>Abrindo o Doc…</p></div>}
        {!tema && !carregando && (
          <div className="empty">
            <h2>Escolha um tema</h2>
            <p>O laboratório abre a versão mais recente do Doc e confere o texto contra os 2.074 municípios, pelo mesmo código do relatório.</p>
          </div>
        )}
        {grupos.map((grupo, i) =>
          grupo.tipo === 'bloco' ? (
            <Bloco key={i} numero={++numeroBloco} versoes={grupo.versoes.map((indice) => itens[indice])} />
          ) : (
            <Texto key={i} item={itens[grupo.indice]} />
          )
        )}
      </main>
    </>
  )
}
