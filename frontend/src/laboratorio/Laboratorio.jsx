import React, { createContext, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import {
  OPERADORES,
  agruparEmBlocos,
  avisosDaVersao,
  blocoAlterado,
  buscarOpcoes,
  camposDaCondicao,
  camposForaDasColunas,
  chaveDoRascunho,
  comNovoBloco,
  condicaoDoItem,
  doRascunho,
  exportar,
  fraseDaCondicao,
  htmlParaODocs,
  inserirColuna,
  lerDoc,
  numeroValido,
  paraRascunho,
  prefixoDoDoc,
  temEdicao,
  textoDoBloco,
  textoDoItem,
  textoQueSai,
  trechoParaLer,
  versaoModelo,
} from './modelo.js'
import { CHAVE_TUTORIAL_VISTO, abrirTutorial, fecharTutorial } from './tutorial.js'

// Em produção, sempre a mesma origem: atrás do gamma-lab.oca-portal.com, o basic auth
// do nginx cobre a página e a API juntas. O build do gamma grava um VITE_API_BASE_URL
// (o do gerador, outro endereço), que mandaria a API para fora do basic auth. Só no dev
// do Vite, que roda noutra porta, ele vale.
const API_BASE = import.meta.env.DEV ? import.meta.env.VITE_API_BASE_URL || '' : ''
const INTERVALO_MS = 1000
const MAX_NOMES = 8
const MAX_SUGESTOES = 12
// O painel de texto pronto espera a pessoa parar de digitar antes de pedir de novo.
const ESPERA_DO_PAINEL_MS = 500

async function pedir(caminho, opcoes) {
  const resposta = await fetch(`${API_BASE}${caminho}`, opcoes)
  const corpo = await resposta.json().catch(() => ({}))
  if (!resposta.ok) throw Object.assign(new Error(corpo.detail || `Erro ${resposta.status}`), { status: resposta.status })
  return corpo
}

const postarJson = (caminho, corpo) =>
  pedir(caminho, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) })

// localStorage pode faltar (aba anônima, dados bloqueados) ou lançar: a página
// funciona sem ele, só sem rascunho (spec, "Rascunho").
const armazem = {
  ler(chave) {
    try {
      return localStorage.getItem(chave)
    } catch {
      return null
    }
  },
  gravar(chave, valor) {
    try {
      localStorage.setItem(chave, valor)
    } catch {
      // sem rascunho
    }
  },
  apagar(chave) {
    try {
      localStorage.removeItem(chave)
    } catch {
      // nada a apagar
    }
  },
}

const dataHora = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
const numero = (n) => n.toLocaleString('pt-BR')

// A unidade do tema (03/11/2026: "Estado e Área de interesse se comportarão como
// município"): as palavras da tela e o parâmetro das rotas. Chega aos componentes pelo
// contexto `Unidade`. `os`, `todos`, `nenhuma` e `conferido` levam o gênero ("todas as áreas").
const UNIDADES = {
  municipio: {
    chave: 'municipio', nome: 'Município', um: 'município', varios: 'municípios', nenhum: 'nenhum município',
    numa: 'numa cidade', nesta: 'nesta cidade', escolha: 'Escolha uma cidade',
    digite: 'Digite o nome da cidade…', comoSai: 'no relatório dela, com os gráficos',
    os: 'os', todos: 'todos os', nenhuma: 'nenhum', conferido: 'conferido',
  },
  estado: {
    chave: 'estado', nome: 'Estado', um: 'estado', varios: 'estados', nenhum: 'nenhum estado',
    numa: 'num estado', nesta: 'neste estado', escolha: 'Escolha um estado',
    digite: 'Digite o nome do estado…', comoSai: 'no relatório dele (sem gráficos: eles são só municipais)',
    os: 'os', todos: 'todos os', nenhuma: 'nenhum', conferido: 'conferido',
  },
  area: {
    chave: 'area', nome: 'Área', um: 'área', varios: 'áreas', nenhum: 'nenhuma área',
    numa: 'numa área', nesta: 'nesta área', escolha: 'Escolha uma área de interesse',
    digite: 'Digite o nome da área…', comoSai: 'no relatório dela (sem gráficos: eles são só municipais)',
    os: 'as', todos: 'todas as', nenhuma: 'nenhuma', conferido: 'conferida',
  },
}
const Unidade = createContext(UNIDADES.municipio)

const contar = (n, u) => `${numero(n)} ${n === 1 ? u.um : u.varios}`
const rota = (u, slug, resto) => `/laboratorio/${slug}/${resto}${u.chave === 'municipio' ? '' : `?unidade=${u.chave}`}`

// Só para a tela: várias linhas em branco seguidas viram uma. A exportação usa o original.
const paraTela = (texto) => texto.trim().replace(/\n\s*\n(\s*\n)+/g, '\n\n')

// Coluna de texto com 2 a 40 valores, fora a sigla da UF e a concordância de estado e área: as
// que o "ler com cada valor" do backend lê (services/laboratorio.py,
// _FORA_DO_LER_COM_CADA_VALOR).
const FORA_DO_LER_COM_CADA_VALOR = new Set([
  'sigla_uf', 'uf_estado', 'uf_sigla_uf', 'uf_sujeito', 'uf_em', 'uf_de',
  'area_nome', 'area_sigla', 'area_sujeito', 'area_em', 'area_de',
])
const comparavel = (info) =>
  info?.tipo === 'texto' && info.distintos >= 2 && info.distintos <= 40 && !FORA_DO_LER_COM_CADA_VALOR.has(info.coluna)

function resumoDaColuna(info, u) {
  // Pode ser apelido que o gerador resolve (_resolver_campo_com_alias): quem diz se
  // sai cru é a conferência.
  if (!info) return 'não existe nos dados do tema: sai cru no relatório'
  if (info.tipo === 'apelido') return `apelido que o gerador resolve: sai de $${info.de}`
  const vazios = info.vazios ? `; vazia em ${contar(info.vazios, u)}` : ''
  if (info.tipo === 'numero') {
    const outros = info.nao_numeros.map((v) => `"${v.valor}" em ${numero(v.municipios)}`).join(', ')
    return `número de ${numero(info.min)} a ${numero(info.max)} ; zero em ${contar(info.zeros, u)}${vazios}${outros ? `; ${outros}` : ''}`
  }
  if (info.tipo === 'texto') return `texto, ${numero(info.distintos)} ${info.distintos === 1 ? 'valor' : 'valores'}${vazios}`
  return `lista${vazios}`
}

// Os valores de uma coluna de texto, todos (a ideia é ver todas as opções). O backend
// manda os 40 mais comuns; acima disso é nome próprio (nm_mun, nome_uc).
function valoresDaColuna(info) {
  if (info?.tipo !== 'texto') return { valores: [], mais: 0 }
  return { valores: info.valores, mais: info.distintos - info.valores.length }
}

// Para o title (passar o mouse): um valor por linha.
function tituloDaColuna(nome, info, u) {
  const { valores, mais } = valoresDaColuna(info)
  const linhas = valores.map((v) => `• ${v.valor} (${numero(v.municipios)})`)
  if (mais) linhas.push(`… e mais ${numero(mais)} valores`)
  return [`$${nome}: ${resumoDaColuna(info, u)}`, ...linhas].join('\n')
}

// O autocomplete oferece só colunas: o apelido existe para Doc antigo, não para texto novo.
const soColunas = (colunas) => [...(colunas ?? [])].filter(([, info]) => info.tipo !== 'apelido').map(([nome]) => nome)

function FichaDaColuna({ nome, info }) {
  const u = useContext(Unidade)
  const { valores, mais } = valoresDaColuna(info)
  return (
    <div className="ficha">
      <b>${nome}</b> <span className="muted">{resumoDaColuna(info, u)}</span>
      {valores.length > 0 && (
        <div className="valores">
          {valores.map((v) => (
            <span key={v.valor} className="chip">{v.valor} <span className="muted">{numero(v.municipios)}</span></span>
          ))}
          {mais > 0 && <span className="muted">… e mais {numero(mais)} valores (nome próprio)</span>}
        </div>
      )}
    </div>
  )
}

// Os $campos do texto com a ficha da coluna ao passar o mouse (spec, "Construir").
function ComCampos({ texto, colunas }) {
  const u = useContext(Unidade)
  if (!colunas) return texto
  return texto.split(/((?:[A-Za-z_][\w-]*\.)?\$[A-Za-z_]\w*)/).map((parte, i) => {
    if (i % 2 === 0) return parte
    const cifrao = parte.indexOf('$')
    const nome = parte.slice(cifrao + 1)
    const info = colunas.get(nome)
    // O prefixo ("tema.") não muda nada para o gerador: fica esmaecido no texto e some
    // na margem, onde ocupava metade da largura.
    return (
      <span key={i} className={`campo${info ? '' : ' desconhecido'}`} title={tituloDaColuna(nome, info, u)}>
        {cifrao > 0 && <span className="prefixo">{parte.slice(0, cifrao)}</span>}{parte.slice(cifrao)}
      </span>
    )
  })
}

// Tira do texto o $campo em que o cursor está (para o aviso não piscar a cada letra).
function semOCampoDoCursor(texto, pos) {
  if (pos === null) return texto
  return texto.replace(/(?:[A-Za-z_][\w-]*\.)?\$\w*/g, (m, i) => (i <= pos && pos <= i + m.length ? '' : m))
}

// Textarea com autocomplete de $coluna: abre ao digitar "$" (com ou sem "tema.") e
// troca só o nome depois do "$". A lista fica embaixo do textarea, não no cursor.
function EditorComColunas({ valor, mudar, colunas, prefixo }) {
  const ref = useRef(null)
  const cursor = useRef(null)
  const [sugestao, setSugestao] = useState(null)
  const [posicaoDoCursor, setPosicaoDoCursor] = useState(null)
  // Aviso enquanto se escreve (André, 03/11: só vinha da conferência, lá no topo). O
  // $campo onde está o cursor fica de fora: "$agua_in" ainda está sendo digitado.
  const errados = sugestao ? [] : camposForaDasColunas(semOCampoDoCursor(valor, posicaoDoCursor), colunas)
  useEffect(() => {
    if (cursor.current === null) return
    ref.current.setSelectionRange(cursor.current, cursor.current)
    cursor.current = null
  })
  // Cresce até caber o texto inteiro. Contar as quebras de linha ignorava a quebra
  // automática e escondia o fim do parágrafo (André, 01/11).
  useLayoutEffect(() => {
    const caixa = ref.current
    caixa.style.height = 'auto'
    caixa.style.height = `${caixa.scrollHeight + 2}px`
  }, [valor])

  function atualizar(alvo) {
    const pos = alvo.selectionStart
    setPosicaoDoCursor(pos)
    const m = alvo.value.slice(0, pos).match(/\$(\w*)$/)
    if (!m || !colunas) return setSugestao(null)
    const q = m[1].toLowerCase()
    const nomes = soColunas(colunas)
    const lista = [
      ...nomes.filter((c) => c.toLowerCase().startsWith(q)),
      ...nomes.filter((c) => !c.toLowerCase().startsWith(q) && c.toLowerCase().includes(q)),
    ].slice(0, MAX_SUGESTOES)
    if (!lista.length || (lista.length === 1 && lista[0].toLowerCase() === q)) return setSugestao(null)
    setSugestao({ inicio: pos - m[1].length, fim: pos, lista, sel: 0 })
  }
  function escolher(nome) {
    const { texto, cursor: pos } = inserirColuna(valor, sugestao.inicio, sugestao.fim, nome, prefixo)
    cursor.current = pos
    mudar(texto)
    setSugestao(null)
  }
  function tecla(e) {
    if (!sugestao) return
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const passo = e.key === 'ArrowDown' ? 1 : -1
      setSugestao({ ...sugestao, sel: (sugestao.sel + passo + sugestao.lista.length) % sugestao.lista.length })
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      escolher(sugestao.lista[sugestao.sel])
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setSugestao(null)
    }
  }

  return (
    <div className="editor">
      <textarea
        ref={ref}
        value={valor}
        rows={4}
        autoFocus
        onChange={(e) => {
          mudar(e.target.value)
          atualizar(e.target)
        }}
        onKeyDown={tecla}
        onKeyUp={(e) => ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key) && atualizar(e.target)}
        onClick={(e) => atualizar(e.target)}
        onBlur={() => {
          setSugestao(null)
          setPosicaoDoCursor(null)
        }}
      />
      {errados.length > 0 && (
        <div className="problema">
          {errados.map((c) => `$${c}`).join(', ')} não {errados.length === 1 ? 'existe' : 'existem'} nos dados do tema: {errados.length === 1 ? 'sai' : 'saem'} cru no relatório.
        </div>
      )}
      {sugestao && (
        <div className="sugestoes" role="listbox">
          {sugestao.lista.map((nome, i) => (
            <div
              key={nome}
              role="option"
              aria-selected={i === sugestao.sel}
              className={i === sugestao.sel ? 'on' : ''}
              onMouseEnter={() => setSugestao({ ...sugestao, sel: i })}
              onMouseDown={(e) => {
                e.preventDefault() // sem isso o blur do textarea fecha a lista antes do clique
                escolher(nome)
              }}
            >
              <b>${nome}</b> <span className="muted">{resumoDaColuna(colunas.get(nome))}</span>
            </div>
          ))}
          <FichaDaColuna nome={sugestao.lista[sugestao.sel]} info={colunas.get(sugestao.lista[sugestao.sel])} />
        </div>
      )}
    </div>
  )
}

// "Nova condição": coluna / operador / valor que escreve a frase na 1ª linha. Depois
// disso a linha é só texto (spec, "Construir").
// Caixa de busca com lista própria, no lugar do <datalist> (cada navegador o desenha do
// seu jeito; no Chrome do Windows, uma lista escura): o mesmo menu do seletor de tema
// (André, 03/11). Padrão combobox do WAI-ARIA: setas, Enter, Esc; clicar abre a lista.
function CaixaDeBusca({ id, valor, mudar, opcoes, placeholder, className = '' }) {
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(0)
  const [lugar, setLugar] = useState(null)
  const raiz = useRef(null)
  const achadas = useMemo(() => buscarOpcoes(opcoes, valor), [opcoes, valor])
  // A lista fica presa à tela, medida a partir do campo: dentro do painel da cidade (que
  // rola), ela seria cortada quando o painel está baixo. Rolar ou redimensionar fecha.
  useLayoutEffect(() => {
    if (!aberto) return
    const r = raiz.current.getBoundingClientRect()
    setLugar({ top: r.bottom + 6, left: r.left, width: r.width })
  }, [aberto])
  useEffect(() => {
    if (!aberto) return
    const fora = (e) => { if (!raiz.current?.contains(e.target)) setAberto(false) }
    const fechar = (e) => { if (!e.target?.closest?.('.seletor-lista')) setAberto(false) }
    document.addEventListener('mousedown', fora)
    window.addEventListener('scroll', fechar, true)
    window.addEventListener('resize', fechar)
    return () => {
      document.removeEventListener('mousedown', fora)
      window.removeEventListener('scroll', fechar, true)
      window.removeEventListener('resize', fechar)
    }
  }, [aberto])
  useEffect(() => {
    if (aberto) document.getElementById(`${id}-${ativo}`)?.scrollIntoView({ block: 'nearest' })
  }, [aberto, ativo, id])
  function escolher(opcao) {
    mudar(opcao)
    setAberto(false)
  }
  function tecla(e) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (!aberto) return setAberto(true)
      const passo = e.key === 'ArrowDown' ? 1 : -1
      setAtivo((i) => (i + passo + achadas.length) % Math.max(achadas.length, 1))
    } else if (e.key === 'Enter' && aberto && achadas[ativo]) {
      e.preventDefault()
      escolher(achadas[ativo])
    } else if (e.key === 'Escape' && aberto) {
      e.preventDefault()
      setAberto(false)
    }
  }
  const mostrar = aberto && lugar && achadas.length > 0 && !(achadas.length === 1 && achadas[0] === valor)
  return (
    <div className={`caixa-busca ${className}`} ref={raiz}>
      <input
        role="combobox"
        aria-expanded={mostrar}
        aria-controls={`${id}-lista`}
        aria-autocomplete="list"
        aria-activedescendant={mostrar ? `${id}-${ativo}` : undefined}
        placeholder={placeholder}
        value={valor}
        onChange={(e) => {
          mudar(e.target.value)
          setAtivo(0)
          setAberto(true)
        }}
        onClick={() => setAberto((a) => !a)}
        onKeyDown={tecla}
      />
      {mostrar && (
        <ul className="seletor-lista lista-busca" role="listbox" id={`${id}-lista`} style={lugar}>
          {achadas.map((opcao, i) => (
            <li
              key={opcao}
              id={`${id}-${i}`}
              role="option"
              aria-selected={opcao === valor}
              className={i === ativo ? 'ativo' : ''}
              onMouseEnter={() => setAtivo(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => escolher(opcao)}
            >
              <span className="nome">{opcao}</span>
              {opcao === valor && <span className="marcado" aria-hidden="true">✓</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function FormCondicao({ colunas, prefixo, escrever, fechar }) {
  const [coluna, setColuna] = useState('')
  const nomesDasColunas = useMemo(() => soColunas(colunas), [colunas])
  const [operador, setOperador] = useState('igual')
  const [valor, setValor] = useState('')
  const [valor2, setValor2] = useState('')
  const info = colunas?.get(coluna)
  const operadores = OPERADORES.filter((o) => info?.tipo === 'numero' || o.texto)
  const op = operadores.find((o) => o.id === operador) ?? operadores[0]
  const valores = [valor, valor2].slice(0, op.valores)
  const pronto = info && valores.every(numeroValido)

  return (
    <div className="form-condicao">
      <div className="acoes">
        <span>Para quando</span>
        <CaixaDeBusca id="nova-condicao-coluna" className="coluna" placeholder="coluna" valor={coluna} mudar={(v) => setColuna(v.replace(/^.*\$/, '').trim())} opcoes={nomesDasColunas} />
        <span>for</span>
        <select value={op.id} onChange={(e) => setOperador(e.target.value)}>
          {operadores.map((o) => <option key={o.id} value={o.id}>{o.rotulo}</option>)}
        </select>
        {op.valores >= 1 && <input className="num" placeholder="número" value={valor} onChange={(e) => setValor(e.target.value)} />}
        {op.valores === 2 && <><span>e</span><input className="num" placeholder="número" value={valor2} onChange={(e) => setValor2(e.target.value)} /></>}
        <button className="btn pri sm" disabled={!pronto} onClick={() => escrever(fraseDaCondicao({ prefixo, coluna, operador: op.id, valor, valor2 }))}>
          trocar a 1ª linha
        </button>
        <button className="btn sm" onClick={fechar}>fechar</button>
      </div>
      {coluna && <FichaDaColuna nome={coluna} info={info} />}
      {info?.tipo === 'texto' && (
        <div className="muted">O gerador só compara números: numa coluna de texto, a condição só pode ser "sem dados" ou "com dados".</div>
      )}
      {valores.some((v) => v && !numeroValido(v)) && (
        <div className="muted">Escreva o número sem sinal, com vírgula ou ponto (ex.: 0,5). O gerador não lê "-1".</div>
      )}
    </div>
  )
}

// Destaca o valor dentro do texto pronto.
function comDestaque(texto, valor) {
  const partes = texto.split(valor)
  return partes.flatMap((parte, i) => (i ? [<mark key={i}>{valor}</mark>, parte] : [parte]))
}

// "Ler com cada valor": o trecho pronto num município de cada valor das colunas de
// texto que ele usa, só onde o trecho sai no relatório (decisão do André, 01/11).
function LerComCadaValor({ tema, texto, colunas, csv }) {
  const u = useContext(Unidade)
  const trecho = trechoParaLer(texto)
  const [lido, setLido] = useState(null)
  const usadas = [...camposDaCondicao(trecho)].filter((c) => comparavel(colunas?.get(c)))
  if (!usadas.length) return null
  // Texto editado ou CSV trocado: a leitura antiga não vale.
  const atual = lido?.trecho === trecho && lido.csv === csv ? lido : null

  async function ler() {
    setLido({ trecho, csv, carregando: true })
    try {
      setLido({ trecho, csv, ...(await postarJson(rota(u, tema, 'cada-valor'), { texto: trecho, csv: csv?.linhas })) })
    } catch (err) {
      setLido({ trecho, csv, erro: err.message })
    }
  }

  if (!atual?.colunas) {
    return (
      <div className="cada-valor">
        <button className="btn ghost sm" onClick={ler} disabled={atual?.carregando}>
          {atual?.carregando ? 'lendo…' : `ler com cada valor de ${usadas.map((c) => `$${c}`).join(', ')}`}
        </button>
        {atual?.erro && <span className="chip ruim">{atual.erro}</span>}
      </div>
    )
  }
  return (
    <div className="cada-valor">
      {atual.colunas.map((c) => (
        <details key={c.coluna} open={atual.colunas.length === 1}>
          <summary><b>${c.coluna}</b> <span className="muted">{c.valores.length} valores</span></summary>
          {c.valores.map((v) => (
            <div key={v.valor} className="valor">
              <div>
                <span className="chip">{v.valor}</span>{' '}
                <span className="muted">
                  {contar(v.municipios, u)}{v.vale_em < v.municipios ? `, o trecho sai em ${numero(v.vale_em)}` : ''}
                </span>
              </div>
              {v.texto ? (
                <div className="exemplo"><span className="muted">{v.cidade}:</span> {comDestaque(v.texto, v.valor)}</div>
              ) : (
                <div className="muted">Com este valor, o trecho não sai em {u.nenhum}.</div>
              )}
            </div>
          ))}
        </details>
      ))}
      <button className="btn ghost sm" onClick={() => setLido(null)}>fechar</button>
    </div>
  )
}

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

function Versao({ item, contagem, avisos, naCidade, podeSeparar, acoes, tema, colunas, prefixo, csv }) {
  const u = useContext(Unidade)
  const texto = textoDoItem(item)
  // Versão recém-criada já abre em edição, com o modelo no textarea.
  const [editando, setEditando] = useState(item.original === '' && item.editado !== undefined)
  const [rascunho, setRascunho] = useState(() => separarEspacos(texto).miolo)
  const [formAberto, setFormAberto] = useState(false)
  const condicao = condicaoDoItem(item)
  const removida = texto === ''
  const estado = item.original === '' ? 'nova' : removida ? 'removida' : item.editado !== undefined ? 'alterada' : null

  function abrirEdicao() {
    setRascunho(separarEspacos(texto).miolo)
    setEditando(true)
  }
  // O texto da versão com o rascunho no miolo; o espaço em volta (linhas em branco do
  // Doc) volta igual.
  function montar(r) {
    const { antes, depois } = separarEspacos(texto)
    return antes + r.trim() + (depois || '\n')
  }
  function salvar() {
    acoes.digitar(null)
    acoes.salvar(montar(rascunho))
    setEditando(false)
  }
  function cancelar() {
    acoes.digitar(null)
    if (item.original === '' && !item.editado.trim()) acoes.desfazer()
    else setEditando(false)
  }
  // O painel de texto pronto acompanha o que se digita, antes do "Pronto".
  useEffect(() => {
    if (editando) acoes.digitar(montar(rascunho))
  }, [editando, rascunho])
  // A versão pode sair da tela no meio da edição (trocar de tema, desfazer): o
  // painel não pode ficar com o texto dela.
  useEffect(() => () => acoes.digitar(null), [])

  if (editando) {
    return (
      <div className="versao editando">
        <EditorComColunas valor={rascunho} mudar={setRascunho} colunas={colunas} prefixo={prefixo} />
        {formAberto && (
          <FormCondicao
            colunas={colunas}
            prefixo={prefixo}
            escrever={(frase) => setRascunho((r) => [frase, ...r.split('\n').slice(1)].join('\n'))}
            fechar={() => setFormAberto(false)}
          />
        )}
        <div className="acoes">
          <button className="btn pri sm" onClick={salvar}>Pronto</button>
          {!formAberto && <button className="btn sm" onClick={() => setFormAberto(true)}>nova condição</button>}
          <button className="btn sm" onClick={cancelar}>Cancelar</button>
        </div>
      </div>
    )
  }

  const classe = (removida ? ' removida' : naCidade === undefined ? '' : naCidade ? ' dispara' : ' apagada') + (avisos.length ? ' com-aviso' : '')
  const corpo = separarEspacos(texto).miolo.split('\n').slice(1).join('\n')
  return (
    // Condição na margem, como anotação de revisor; o texto corre ao lado (André, 03/11).
    <div className={`versao${classe}`} id={`item-${item.id}`}>
      <div className="margem">
        <span className={`condicao${condicao || removida ? '' : ' quebrada'}`}>
          {removida ? item.condicao : condicao ? <ComCampos texto={condicao} colunas={colunas} /> : 'A 1ª linha não é mais uma condição: o gerador vai ler isto como texto fixo'}
        </span>
        <div className="margem-info">
        {estado && <span className={`chip ${estado === 'removida' ? 'ruim' : 'atencao'}`}>{estado}</span>}
        {contagem !== undefined && !removida && (
          contagem
            ? <span className="muted">aparece em {contar(contagem, u)}</span>
            : <span className="chip ruim">não aparece em {u.nenhum}</span>
        )}
        {naCidade && !removida && <span className="na-cidade">vale {u.nesta}</span>}
        </div>
        <div className="margem-acoes">
        {estado && <button className="btn ghost sm" onClick={acoes.desfazer}>desfazer</button>}
        {!removida && <button className="btn sm" onClick={abrirEdicao}>editar</button>}
        {!removida && podeSeparar && <button className="btn ghost sm" onClick={acoes.separar} title="Esta versão e as de baixo passam a ser outro bloco">separar daqui</button>}
        {!removida && <button className="btn ghost sm" onClick={acoes.remover}>remover</button>}
        </div>
      </div>
      <div className="texto-versao">
        {avisos.map((a) => <div key={a} className="problema">{a}</div>)}
        {!removida && <div className="corpo"><ComCampos texto={paraTela(corpo)} colunas={colunas} /></div>}
        {!removida && <LerComCadaValor tema={tema} texto={texto} colunas={colunas} csv={csv} />}
      </div>
    </div>
  )
}

function Texto({ item, avisos, tema, colunas, csv }) {
  return (
    <div className={`card texto${avisos.length ? ' com-aviso' : ''}`} id={`item-${item.id}`}>
      {avisos.map((a) => <div key={a} className="problema">{a}</div>)}
      <div className="cbody"><ComCampos texto={paraTela(textoDoItem(item))} colunas={colunas} /></div>
      <LerComCadaValor tema={tema} texto={textoDoItem(item)} colunas={colunas} csv={csv} />
    </div>
  )
}

function Bloco({ numero: n, versoes, estatisticas, completo, juntar, novaVersao, alterado, dica, copiar, copiado }) {
  const u = useContext(Unidade)
  return (
    <div className="card" id={`bloco-${n}`}>
      <div className="chead">
        <span className="ctag">Bloco {n}</span>
        <span className="chip">{versoes.length} {versoes.length === 1 ? 'versão' : 'versões'}</span>
        {alterado ? <span className="chip atencao">alterado</span> : <span className="chip bom">igual ao Doc</span>}
        {estatisticas?.sem.length > 0 && <span className="chip ruim">sem texto em {contar(estatisticas.sem.length, u)}</span>}
        {estatisticas?.sem.length === 0 && completo && <span className="chip bom">texto em {u.todos} {u.varios}</span>}
        {estatisticas?.varias.length > 0 && <span className="chip ruim">sai com 2+ trechos em {contar(estatisticas.varias.length, u)}</span>}
        <span className="spacer" />
        {juntar && <button className="btn ghost sm" onClick={juntar}>juntar com o de cima</button>}
        <button className={`btn sm${alterado ? ' pri' : ''}`} onClick={copiar} title="Copia o bloco para colar no Doc, por cima do mesmo trecho">
          {copiado ? 'copiado ✓' : 'copiar bloco'}
        </button>
      </div>
      {alterado && dica && <div className="bloco-detalhe">{dica}</div>}
      {estatisticas && (estatisticas.sem.length > 0 || estatisticas.varias.length > 0) && (
        <div className="bloco-detalhe">
          {estatisticas.varias.length > 0 && (
            <div>
              <b>Sai com 2+ trechos em:</b> <Nomes nomes={estatisticas.varias.slice(0, MAX_NOMES)} total={estatisticas.varias.length} />
              <div className="muted">Se são parágrafos seguidos que devem sair juntos, não é erro: use "separar daqui" na versão que começa o outro assunto.</div>
            </div>
          )}
          {estatisticas.sem.length > 0 && (
            <div><b>Sem texto em:</b> <Nomes nomes={estatisticas.sem.slice(0, MAX_NOMES)} total={estatisticas.sem.length} /></div>
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

// O 1º e o último bloco do tema levam o marcador junto (textoDoBloco): a editora
// precisa selecionar no Doc a linha inteira, com ele.
function dicaDeColar(texto) {
  const abre = texto.startsWith('descricao_tema')
  const fecha = texto.endsWith('@@')
  if (!abre && !fecha) return null
  const marcas = [abre && 'começa com "descricao_tema = “"', fecha && 'termina com "”@@"'].filter(Boolean).join(' e ')
  return `Este bloco ${marcas}, que marca o tema no Doc. Selecione no Doc as linhas inteiras do bloco, com essa marca: ela vai junto na cópia.`
}

// Resumo para levar ao Doc (spec, "Exportar"): copiar por bloco é o caminho
// principal; copiar o tema inteiro é o secundário, porque colar o Doc inteiro apaga
// comentários e formatação que o editorial tenha nele.
function PainelExportar({ editou, alterados, conferencia, nAvisos, copiarTudo, copiado }) {
  return (
    <div className="card exportar">
      <div className="chead"><span className="ctag">Para levar ao Doc</span></div>
      <div className="cbody">
        <div>
          {!editou ? 'Nada alterado ainda: edite uma versão e o bloco aparece aqui para copiar.' : alterados.length
            ? <>Blocos alterados: {alterados.map((n, i) => <span key={n}>{i ? ', ' : ''}<a href={`#bloco-${n}`}>Bloco {n}</a></span>)}. Copie cada um e cole no Doc por cima do mesmo trecho.</>
            : 'Nenhum bloco alterado: as mudanças estão em texto fora dos blocos.'}
        </div>
        {editou && <div className={conferencia === 'ok' ? 'muted' : 'aviso-exportar'}>
          {conferencia === 'ok' && '✓ Conferido depois da última mudança.'}
          {conferencia === 'velha' && 'O texto mudou desde a última conferência: confira antes de colar (barra no pé da página).'}
          {conferencia === 'nunca' && 'Ainda não conferido: confira antes de colar (barra no pé da página).'}
        </div>}
        {nAvisos > 0 && <div className="aviso-exportar">{nAvisos === 1 ? '1 trecho' : `${nAvisos} trechos`} com aviso, marcados em vermelho: "próximo aviso", na barra do pé da página, leva a cada um.</div>}
        <div className="acoes">
          <button className="btn sm" onClick={copiarTudo}>{copiado ? 'copiado ✓' : 'copiar o Doc inteiro'}</button>
          <span className="muted">Só se for substituir o Doc todo: colar por cima apaga comentários e formatação do Doc.</span>
        </div>
      </div>
    </div>
  )
}

// Sem permissão de área de transferência (http, navegador antigo): o texto fica
// selecionado num campo para Ctrl+C.
function CopiarAMao({ texto, fechar }) {
  return (
    <div className="copiar-a-mao">
      <div className="card">
        <div className="chead"><span className="ctag">Copie com Ctrl+C</span><span className="spacer" /><button className="btn sm" onClick={fechar}>fechar</button></div>
        <div className="aviso-exportar">Este navegador não deixou copiar direto. Colado no Google Docs a partir daqui, todo trecho entre dois "$" vira equação e some do relatório: prefira abrir o TemaLab pelo endereço https.</div>
        <textarea readOnly value={texto} autoFocus onFocus={(e) => e.target.select()} />
      </div>
    </div>
  )
}

// "Veja o texto pronto numa cidade" (André, 01/11): ao lado dos blocos, o tema como sai
// no relatório da cidade, com os gráficos dela, acompanhando o que se escreve. O HTML
// vem do mesmo render do relatório (html_do_tema), que escapa o texto do Doc e os
// valores, inclusive os de um CSV (conferido em 01/11: "<script>" sai como texto).
function PainelCidade({ cidade, setCidade, cidades, resultado, atualizando, erro }) {
  const u = useContext(Unidade)
  return (
    <aside className="painel">
      <div className="painel-topo">
        <b>Veja o texto pronto {u.numa}</b>
        <CaixaDeBusca id="cidade" className="cidade" placeholder={u.digite} valor={cidade} mudar={setCidade} opcoes={cidades} />
        {atualizando && <span className="muted">atualizando…</span>}
      </div>
      {erro && <div className="banner erro">{erro}</div>}
      {!resultado && !atualizando && !erro && (
        <p className="muted vazio">
          {u.escolha} para ver o tema como sai {u.comoSai}. O texto acompanha o que você escreve.
        </p>
      )}
      {resultado && (
        <div className={`relatorio${atualizando ? ' velho' : ''}`} dangerouslySetInnerHTML={{ __html: resultado.html.join('') }} />
      )}
    </aside>
  )
}

// Só o que não tem um trecho onde ficar: os campos crus e as condições não entendidas
// vão para a versão que os usa (André, 03/11); aqui ficam os que não acharam versão.
function Avisos({ resultado, crusSoltos, naoEntendidasSoltas }) {
  const u = useContext(Unidade)
  const avisos = []
  for (const campo of crusSoltos) {
    avisos.push(
      <div key={`c-${campo.campo}`} className={`banner ${campo.existe ? 'atencao' : 'erro'}`}>
        <b>${campo.campo}</b>{' '}
        {campo.existe
          ? `existe, mas está vazio em ${contar(campo.municipios.length, u)} e sai cru no texto: `
          : `não existe nos dados de ${u.nenhum} e sai cru no texto. `}
        {campo.existe && <Nomes nomes={campo.municipios.slice(0, MAX_NOMES)} total={campo.municipios.length} />}
      </div>
    )
  }
  for (const aviso of naoEntendidasSoltas) {
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
    avisos.push(<div key="erros" className="banner erro"><b>Erro em {contar(erros.length, u)}:</b> {erros.slice(0, 3).map(([c, e]) => `${c} (${e})`).join('; ')}</div>)
  }
  return avisos
}

// Conferir perto de quem edita (André, 03/11): o botão e o resultado ficavam no topo, e
// quem editava o Bloco 7 não via nada. A barra gruda no pé da coluna do texto. A
// cobertura responde a pergunta do editorial: toda cidade recebe texto em todo bloco?
function BarraDaConferencia({ conferencia, rodando, resultado, velha, casa, cobertura, nBlocos, nAvisos, proximo, conferir }) {
  const u = useContext(Unidade)
  let status
  let tom = ''
  if (rodando) {
    status = conferencia.estado === 'na_fila'
      ? 'Na fila: outra conferência está rodando…'
      : `Conferindo ${numero(conferencia.feitos)} de ${numero(conferencia.total)} ${u.varios}…`
  } else if (conferencia?.estado === 'erro') {
    status = `A conferência falhou: ${conferencia.erro}`
    tom = ' ruim'
  } else if (!resultado) {
    status = `Ainda não conferido contra ${u.os} ${u.varios}.`
  } else if (velha) {
    status = `O texto mudou desde a conferência das ${dataHora(conferencia.conferido_em)}: as contagens são do texto anterior.`
    tom = ' atencao'
  } else if (!casa) {
    status = 'As versões do texto não batem com as da conferência: confira de novo.'
    tom = ' atencao'
  } else {
    const nenhum = resultado.versoes.filter((v) => !v.municipios).length
    status = `Conferido às ${dataHora(conferencia.conferido_em)} contra ${contar(cobertura.conferidos, u)}.${nenhum ? ` ${nenhum} ${nenhum === 1 ? 'versão não aparece' : 'versões não aparecem'} em ${u.nenhuma}.` : ''}`
  }
  return (
    <div className="barra-conferencia" role="status">
      <div className="barra-linha">
        <span className={`barra-status${tom}`}>{status}</span>
        <span className="spacer" />
        {nAvisos > 0 && (
          <button className="btn sm" onClick={proximo} title="Rola até o próximo trecho marcado em vermelho">
            próximo aviso ↓ <span className="contador">{nAvisos}</span>
          </button>
        )}
        <button className="btn pri sm" onClick={conferir} disabled={rodando}>{resultado ? 'Conferir de novo' : 'Conferir'}</button>
      </div>
      {rodando && (
        <div className="progresso">
          <div className="barra" style={{ width: `${conferencia.total ? (100 * conferencia.feitos) / conferencia.total : 0}%` }} />
        </div>
      )}
      {cobertura && nBlocos > 0 && (
        <div className="cobertura">
          {cobertura.blocosSemTexto.length === 0 ? (
            <span className={cobertura.completa ? 'bom' : ''}>
              {cobertura.completa ? '✓ ' : ''}{nBlocos === 1 ? 'O bloco tem' : `Todos os ${nBlocos} blocos têm`} texto em {cobertura.completa ? `${u.todos} ` : ''}{contar(cobertura.conferidos, u)}{cobertura.completa ? '' : ' conferidos'}.
            </span>
          ) : (
            <span className="ruim">
              {cobertura.blocosSemTexto.length} de {nBlocos} blocos deixam {u.varios} sem texto:{' '}
              {cobertura.blocosSemTexto.map((n, i) => <span key={n}>{i ? ', ' : ''}<a href={`#bloco-${n}`}>Bloco {n}</a></span>)}.
            </span>
          )}
          {cobertura.comErro > 0 && <span className="ruim"> {contar(cobertura.comErro, u)} {cobertura.comErro === 1 ? `deu erro e não foi ${u.conferido}` : `deram erro e não foram ${u.conferido}s`}.</span>}
          {cobertura.ausentes.length > 0 && (
            <span className="atencao">
              {' '}{contar(cobertura.ausentes.length, u)} sem dados neste tema {cobertura.ausentes.length === 1 ? 'ficou' : 'ficaram'} fora:{' '}
              <Nomes nomes={cobertura.ausentes.slice(0, MAX_NOMES)} total={cobertura.ausentes.length} />.
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// Os temas como a unidade os vê: em estado ou área, a data é a do snapshot dela, e o tema
// sem dados ou sem Doc ainda aparece desligado com o motivo (/laboratorio/temas).
function temasDaUnidade(temas, unidade) {
  if (!temas) return []
  if (unidade === 'municipio') return temas
  return temas.map((t) => {
    const daUnidade = t.unidades?.[unidade]
    const motivo = !daUnidade?.snapshot_gerado_em ? 'sem dados ainda' : !daUnidade.tem_doc ? 'sem Doc ainda' : null
    return { ...t, snapshot_gerado_em: daUnidade?.snapshot_gerado_em ?? null, motivo }
  })
}

// Seletor de tema próprio (André, 03/11): a lista nativa não se estiliza, e "Escolha o
// tema" como opção confundia; agora é só o texto do botão enquanto nada foi escolhido.
// Padrão listbox do WAI-ARIA: setas, Home/End, Enter, Esc e a inicial do tema.
function SeletorDeTema({ temas, tema, escolher, desligado }) {
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(0)
  const raiz = useRef(null)
  const botao = useRef(null)
  const lista = useRef(null)
  const opcoes = temas ?? []
  const atual = opcoes.find((t) => t.slug === tema)
  const pode = (t) => Boolean(t?.snapshot_gerado_em) && !t.motivo

  useEffect(() => {
    if (!aberto) return
    lista.current?.focus()
    const fora = (e) => { if (!raiz.current?.contains(e.target)) setAberto(false) }
    document.addEventListener('mousedown', fora)
    return () => document.removeEventListener('mousedown', fora)
  }, [aberto])

  function abrir() {
    setAtivo(Math.max(0, opcoes.findIndex((t) => t.slug === tema)))
    setAberto(true)
  }
  function fechar() {
    setAberto(false)
    botao.current?.focus()
  }
  function confirmar(i) {
    if (!pode(opcoes[i])) return
    fechar()
    if (opcoes[i].slug !== tema) escolher(opcoes[i].slug)
  }
  // Próxima opção com dados a partir de i, andando de passo em passo.
  function proxima(i, passo) {
    for (let n = 0; n < opcoes.length; n++) {
      i = (i + passo + opcoes.length) % opcoes.length
      if (pode(opcoes[i])) return i
    }
    return i
  }
  function tecla(e) {
    const acoes = {
      ArrowDown: () => setAtivo(proxima(ativo, 1)),
      ArrowUp: () => setAtivo(proxima(ativo, -1)),
      Home: () => setAtivo(proxima(-1, 1)),
      End: () => setAtivo(proxima(opcoes.length, -1)),
      Enter: () => confirmar(ativo),
      ' ': () => confirmar(ativo),
      Escape: fechar,
      Tab: () => setAberto(false),
    }
    if (acoes[e.key]) {
      if (e.key !== 'Tab') e.preventDefault()
      return acoes[e.key]()
    }
    if (e.key.length === 1) {
      const letra = e.key.toLowerCase()
      const achado = opcoes.findIndex((t, i) => i > ativo && pode(t) && t.nome.toLowerCase().startsWith(letra))
      const i = achado >= 0 ? achado : opcoes.findIndex((t) => pode(t) && t.nome.toLowerCase().startsWith(letra))
      if (i >= 0) setAtivo(i)
    }
  }

  return (
    <div className="seletor-tema" ref={raiz}>
      <button
        ref={botao}
        type="button"
        className="seletor-botao"
        aria-haspopup="listbox"
        aria-expanded={aberto}
        aria-labelledby="rotulo-tema seletor-botao"
        id="seletor-botao"
        disabled={desligado}
        onClick={() => (aberto ? setAberto(false) : abrir())}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault()
            abrir()
          }
        }}
      >
        {atual ? <><span className="ponto" style={{ background: atual.cor }} />{atual.nome}</> : <span className="sem-tema">Escolha um tema</span>}
      </button>
      {aberto && (
        <ul
          ref={lista}
          className="seletor-lista"
          role="listbox"
          tabIndex={-1}
          aria-labelledby="rotulo-tema"
          aria-activedescendant={`opcao-tema-${ativo}`}
          onKeyDown={tecla}
        >
          {opcoes.map((t, i) => (
            <li
              key={t.slug}
              id={`opcao-tema-${i}`}
              role="option"
              aria-selected={t.slug === tema}
              aria-disabled={!pode(t)}
              className={i === ativo && pode(t) ? 'ativo' : ''}
              onMouseEnter={() => pode(t) && setAtivo(i)}
              onClick={() => confirmar(i)}
            >
              <span className="ponto" style={{ background: t.cor }} />
              <span className="nome">{t.nome}</span>
              {!pode(t) && <span className="sem-dados">{t.motivo ?? 'sem dados ainda'}</span>}
              {t.slug === tema && <span className="marcado" aria-hidden="true">✓</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function Laboratorio() {
  // A altura do cabeçalho muda (barra de progresso, quebra de linha em tela estreita); o
  // painel da cidade e as âncoras dos blocos se alinham por ela (--altura-header).
  const cabecalho = useRef(null)
  useLayoutEffect(() => {
    const observador = new ResizeObserver(([e]) =>
      document.documentElement.style.setProperty('--altura-header', `${e.borderBoxSize[0].blockSize}px`))
    if (cabecalho.current) observador.observe(cabecalho.current)
    return () => observador.disconnect()
  }, [])
  const [temas, setTemas] = useState(null)
  const [desligado, setDesligado] = useState(false)
  const [tema, setTema] = useState('')
  const [unidade, setUnidade] = useState('municipio')
  const u = UNIDADES[unidade]
  const [doc, setDoc] = useState(null)
  const [itens, setItens] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [conferencia, setConferencia] = useState(null)
  const [cidades, setCidades] = useState([])
  const [cidade, setCidade] = useState('')
  // Estados e áreas vêm do snapshot (/laboratorio/temas): quais áreas existem é da equipe
  // de dados, e a tela não supõe (André, 08/11/2026).
  const lugares = unidade === 'municipio' ? cidades : temas?.find((t) => t.slug === tema)?.unidades?.[unidade]?.lugares ?? []
  const [naCidade, setNaCidade] = useState(null)
  const [aoVivo, setAoVivo] = useState(null) // {id, texto}: a versão sendo editada, antes do "Pronto"
  const [atualizandoPainel, setAtualizandoPainel] = useState(false)
  const [erroPainel, setErroPainel] = useState('')
  const pedidoDoPainel = useRef(0)
  const [ajustes, setAjustes] = useState({ cortes: new Set(), juncoes: new Set() })
  const [textoConferido, setTextoConferido] = useState(null)
  const [colunas, setColunas] = useState(null)
  const [rascunho, setRascunho] = useState(null) // {tipo: restaurado | doc_mudou | antigo, ...}
  const [hashBase, setHashBase] = useState(null) // hash do Doc em que o texto da tela se baseia
  const [copiado, setCopiado] = useState(null)
  const [paraCopiar, setParaCopiar] = useState(null)
  // CSV que a editora subiu: só nesta aba, na memória (spec: o servidor não guarda, e
  // uma view inteira tem MBs demais para o localStorage). {nome, linhas, casados, ...}
  const [csv, setCsv] = useState(null)
  const [lendoCsv, setLendoCsv] = useState(false)
  // Tema e unidade abertos agora ("demografia|estado"): resposta que chega depois de
  // trocar um dos dois é descartada.
  const temaVivo = useRef('')
  const vivo = (slug, un) => `${slug}|${un.chave}`
  const proximoId = useRef(0)

  useEffect(() => {
    pedir('/laboratorio/temas')
      .then((lista) => {
        setTemas(lista)
        // ?tema=<slug>[&unidade=estado|area] abre direto: dá para mandar o link de um tema.
        const params = new URLSearchParams(window.location.search)
        const doLink = params.get('tema')
        const unidadeDoLink = UNIDADES[params.get('unidade')] ? params.get('unidade') : 'municipio'
        const t = temasDaUnidade(lista, unidadeDoLink).find((t) => t.slug === doLink)
        if (t?.snapshot_gerado_em && !t.motivo) {
          setUnidade(unidadeDoLink)
          abrirTema(doLink, unidadeDoLink)
        }
      })
      .catch((err) => (err.status === 404 ? setDesligado(true) : setErro(err.message)))
    pedir('/cities').then(setCidades).catch(() => {})
  }, [])

  async function abrirTema(slug, novaUnidade = unidade) {
    const un = UNIDADES[novaUnidade]
    temaVivo.current = vivo(slug, un)
    setTema(slug)
    setDoc(null)
    setItens([])
    setErro('')
    setConferencia(null)
    setNaCidade(null)
    setAjustes({ cortes: new Set(), juncoes: new Set() })
    setColunas(null)
    setRascunho(null)
    setCsv(null)
    setAoVivo(null)
    if (!slug) return
    // Em paralelo com o Doc: sem as colunas, a tela funciona, só sem a ajuda.
    carregarColunas(slug, un)
    setCarregando(true)
    try {
      const aberto = await pedir(rota(un, slug, 'doc'))
      setDoc({ ...aberto, aberto_em: new Date().toISOString() })
      const lidos = lerDoc(aberto.texto)
      proximoId.current = lidos.length
      setItens(lidos)
      setHashBase(aberto.hash)
      const salvo = doRascunho(armazem.ler(chaveDoRascunho(slug, un.chave)) ?? '')
      if (salvo && salvo.hash === aberto.hash) {
        aplicarRascunho(salvo)
        setRascunho({ tipo: 'restaurado', salvo_em: salvo.salvo_em })
      } else if (salvo) {
        setRascunho({ tipo: 'doc_mudou', salvo })
      }
    } catch (err) {
      setErro(err.message)
    } finally {
      setCarregando(false)
    }
  }

  function carregarColunas(slug, un = u) {
    pedir(rota(un, slug, 'colunas'))
      .then((r) => temaVivo.current === vivo(slug, un) && setColunas(new Map(r.colunas.map((c) => [c.coluna, c]))))
      .catch((err) => temaVivo.current === vivo(slug, un) && setErro(`Colunas do tema: ${err.message}`))
  }

  // Trocar a unidade abre o mesmo tema na outra, se ele tiver dados e Doc lá; a cidade
  // escolhida não existe na outra unidade.
  function trocarUnidade(nova) {
    if (nova === unidade) return
    setUnidade(nova)
    setCidade('')
    const t = temasDaUnidade(temas, nova).find((t) => t.slug === tema)
    abrirTema(t?.snapshot_gerado_em && !t.motivo ? tema : '', nova)
  }

  // O arquivo vem em UTF-8 ou, se exportado do Excel, em Windows-1252: o UTF-8 de um
  // arquivo Windows-1252 sai com "�", e aí ele é lido de novo (como no protótipo).
  async function usarCsv(arquivo) {
    if (!arquivo) return
    const slug = tema
    setErro('')
    setLendoCsv(true)
    try {
      let texto = await arquivo.text()
      if (texto.includes('\uFFFD')) texto = new TextDecoder('windows-1252').decode(await arquivo.arrayBuffer())
      const lido = await postarJson(rota(u, slug, 'csv'), { csv: texto })
      if (temaVivo.current !== vivo(slug, u)) return
      trocarCsv({ ...lido, nome: arquivo.name })
      setColunas(new Map(lido.colunas.map((c) => [c.coluna, c])))
    } catch (err) {
      setErro(`CSV: ${err.message}`)
    } finally {
      setLendoCsv(false)
    }
  }
  function tirarCsv() {
    trocarCsv(null)
    carregarColunas(tema)
  }
  // Dados novos: a conferência anterior não vale mais, e o texto numa cidade é refeito.
  function trocarCsv(novo) {
    setCsv(novo)
    setConferencia(null)
  }

  function aplicarRascunho(salvo) {
    setItens(salvo.itens)
    setAjustes(salvo.ajustes)
    proximoId.current = salvo.proximoId
    setHashBase(salvo.hash)
  }
  function descartarRascunho() {
    if (!window.confirm('Descartar o rascunho? As edições somem e o texto volta ao Doc atual.')) return
    armazem.apagar(chaveDoRascunho(tema, unidade))
    const lidos = lerDoc(doc.texto)
    proximoId.current = lidos.length
    setAjustes({ cortes: new Set(), juncoes: new Set() })
    setHashBase(doc.hash)
    setRascunho(null)
    mudarItens(lidos)
  }

  // O rascunho acompanha cada mudança; sem edição nenhuma, não há rascunho. Enquanto a
  // editora não escolhe entre o rascunho antigo e o Doc atual, nada é gravado (senão o
  // Doc atual, sem edição, apagaria o rascunho).
  useEffect(() => {
    if (!doc || !tema || rascunho?.tipo === 'doc_mudou') return
    if (temEdicao(itens)) {
      armazem.gravar(chaveDoRascunho(tema, unidade), paraRascunho({ hash: hashBase, itens, ajustes, proximoId: proximoId.current }))
    } else {
      armazem.apagar(chaveDoRascunho(tema, unidade))
    }
  }, [itens, ajustes])

  async function copiar(texto, rotulo) {
    try {
      // Com o HTML junto: o Docs cola o HTML, e texto puro vira equação (htmlParaODocs).
      await navigator.clipboard.write([new ClipboardItem({
        'text/plain': new Blob([texto], { type: 'text/plain' }),
        'text/html': new Blob([htmlParaODocs(texto)], { type: 'text/html' }),
      })])
      setCopiado(rotulo)
      setTimeout(() => setCopiado((atual) => (atual === rotulo ? null : atual)), 2500)
    } catch {
      setParaCopiar(texto)
    }
  }

  async function conferir() {
    const slug = tema
    setErro('')
    setConferencia({ estado: 'na_fila' })
    const texto = exportar(itens)
    setTextoConferido(texto)
    try {
      const { id } = await postarJson(rota(u, slug, 'conferencias'), { texto, csv: csv?.linhas })
      for (;;) {
        await new Promise((r) => setTimeout(r, INTERVALO_MS))
        if (temaVivo.current !== vivo(slug, u)) return // trocou de tema ou de unidade no meio
        const estado = await pedir(`/laboratorio/conferencias/${id}`)
        setConferencia({ ...estado, conferido_em: new Date().toISOString() })
        if (estado.estado === 'pronta' || estado.estado === 'erro') return
      }
    } catch (err) {
      setConferencia(null)
      setErro(err.message)
    }
  }

  // Toda mudança no texto passa por aqui. O painel de texto pronto acompanha sozinho
  // (efeito abaixo); a conferência inteira, não (~25 s), e a tela avisa que ficou velha.
  function mudarItens(novos) {
    setItens(novos)
  }
  const acoesDaVersao = (id) => ({
    salvar: (texto) =>
      mudarItens(itens.map((i) => (i.id !== id ? i : texto === i.original ? { ...i, editado: undefined } : { ...i, editado: texto }))),
    remover: () => mudarItens(itens.map((i) => (i.id === id ? { ...i, editado: '' } : i))),
    desfazer: () =>
      mudarItens(itens.flatMap((i) => (i.id !== id ? [i] : i.original === '' ? [] : [{ ...i, editado: undefined }]))),
    separar: () =>
      setAjustes(({ cortes, juncoes }) => ({ cortes: new Set(cortes).add(id), juncoes: new Set([...juncoes].filter((j) => j !== id)) })),
    // Só limpa se for desta versão: os ids recomeçam do 0 em cada tema.
    digitar: (texto) => setAoVivo((atual) => (texto !== null ? { id, texto } : atual?.id === id ? null : atual)),
  })
  function juntarComOdeCima(id) {
    setAjustes(({ cortes, juncoes }) => ({ cortes: new Set([...cortes].filter((c) => c !== id)), juncoes: new Set(juncoes).add(id) }))
  }
  function novaVersao(depoisDoId) {
    const nova = {
      id: proximoId.current++,
      tipo: 'versao',
      original: '',
      editado: `\n${versaoModelo(prefixo)}\n`,
      condicao: null,
    }
    const posicaoNoTexto = itens.findIndex((i) => i.id === depoisDoId) + 1
    // Fica no bloco onde foi criada, mesmo antes de a editora trocar o $campo do modelo.
    setAjustes(({ cortes, juncoes }) => ({ cortes, juncoes: new Set(juncoes).add(nova.id) }))
    mudarItens([...itens.slice(0, posicaoNoTexto), nova, ...itens.slice(posicaoNoTexto)])
  }

  // Depois do último bloco, ou o tema inteiro num Doc vazio (comNovoBloco).
  function novoBloco() {
    const novo = comNovoBloco(itens, prefixo, () => proximoId.current++)
    if (!novo) return
    setAjustes(({ cortes, juncoes }) => ({ cortes: new Set(cortes).add(novo.id), juncoes }))
    mudarItens(novo.itens)
  }

  const grupos = useMemo(() => agruparEmBlocos(itens, ajustes), [itens, ajustes])
  const textoSalvo = useMemo(() => exportar(itens), [itens])
  // O que o painel mostra: o texto com a versão em edição como está agora.
  const textoDoPainel = useMemo(
    () => (aoVivo ? exportar(itens.map((i) => (i.id === aoVivo.id ? { ...i, editado: aoVivo.texto } : i))) : textoSalvo),
    [itens, aoVivo, textoSalvo],
  )
  useEffect(() => {
    const valida = lugares.includes(cidade) || csv?.so_no_csv.includes(cidade)
    if (!tema || !doc || !valida) {
      pedidoDoPainel.current++
      setNaCidade(null)
      setAtualizandoPainel(false)
      return
    }
    const numero = ++pedidoDoPainel.current
    setAtualizandoPainel(true)
    const espera = setTimeout(async () => {
      // Só a linha desta cidade: o CSV inteiro a cada tecla pesaria na conexão.
      const linha = csv?.linhas[cidade]
      try {
        const corpo = { texto: textoDoPainel, cidade, csv: linha ? { [cidade]: linha } : undefined, graficos: true }
        const r = await postarJson(rota(u, tema, 'municipio'), corpo)
        if (numero !== pedidoDoPainel.current) return // chegou depois de um pedido mais novo
        setNaCidade({ cidade, texto: textoDoPainel, ...r })
        setErroPainel('')
      } catch (err) {
        if (numero === pedidoDoPainel.current) setErroPainel(err.message)
      } finally {
        if (numero === pedidoDoPainel.current) setAtualizandoPainel(false)
      }
    }, ESPERA_DO_PAINEL_MS)
    return () => clearTimeout(espera)
  }, [textoDoPainel, cidade, csv, tema, doc, lugares])
  // "Vale nesta cidade" nos blocos: só quando o painel é do texto salvo (as posições
  // das versões mudam enquanto se edita uma condição).
  const naCidadeAtual = naCidade && naCidade.texto === textoSalvo ? naCidade : null
  const prefixo = useMemo(() => prefixoDoDoc(doc?.texto ?? '', tema), [doc, tema])
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
  const conferenciaVelha = resultado && textoConferido !== textoSalvo
  // O aviso do gerador começa com a linha da condição, igual à que a conferência
  // devolve para a versão: vai para baixo da linha (spec, "Construir").
  const problemas = new Map(
    (resultado?.condicoes_nao_entendidas ?? []).map((aviso) => {
      const [linha, ...detalhes] = aviso.split('\n')
      return [linha.trim(), detalhes.map((d) => d.replace(/^\s*→\s*/, '')).join('; ')]
    }),
  )
  const opcoesDeTema = useMemo(() => temasDaUnidade(temas, unidade), [temas, unidade])
  const temaAtual = opcoesDeTema.find((t) => t.slug === tema)
  const contaCom = casaComOTexto && !conferenciaVelha
  const blocos = grupos.filter((g) => g.tipo === 'bloco').map((g, i) => ({
    ...g,
    numero: i + 1,
    alterado: blocoAlterado(itens, g.versoes),
    dica: dicaDeColar(textoDoBloco(itens, g.versoes)),
    estatisticas: contaCom
      ? estatisticasDoBloco(g.versoes.map((indice) => posicao.get(indice)).filter((k) => k !== undefined), resultado.versoes_por_municipio)
      : null,
  }))

  // Avisos de cada trecho, no próprio trecho (André, 03/11). Os da tela valem sempre;
  // os da conferência, só se ela é do texto de agora.
  const crusAchados = new Set()
  const avisosDoItem = new Map()
  itens.forEach((item, indice) => {
    const locais = avisosDaVersao(item, colunas)
    const avisos = [...locais]
    const k = posicao.get(indice)
    if (contaCom && textoDoItem(item) !== '') {
      const problema = k !== undefined && problemas.get(resultado.versoes[k].condicao)
      if (problema) avisos.push(`O gerador não entende esta condição: ${problema}`)
      const usados = camposDaCondicao(textoQueSai(item))
      for (const campo of resultado.campos_crus) {
        if (!usados.has(campo.campo)) continue
        crusAchados.add(campo.campo)
        if (locais.some((a) => a.startsWith(`$${campo.campo} `))) continue // já avisado pela tela
        // Só onde este trecho sai: vazio numa cidade em que a versão não vale não aparece.
        const onde = k === undefined ? campo.municipios : campo.municipios.filter((c) => resultado.versoes_por_municipio[c]?.includes(k))
        if (!onde.length) continue
        avisos.push(`$${campo.campo} ${campo.existe ? 'está vazio' : 'não existe'} em ${contar(onde.length, u)} onde este trecho sai, e lá sai cru: ${onde.slice(0, 3).join(', ')}${onde.length > 3 ? '…' : ''}`)
      }
    }
    if (avisos.length) avisosDoItem.set(indice, avisos)
  })
  const semAvisos = []
  const avisosDe = (indice) => avisosDoItem.get(indice) ?? semAvisos
  // Na ordem da tela: o bloco (sem texto / 2+ trechos) antes das versões dele.
  const marcados = []
  let contaBlocos = 0
  for (const grupo of grupos) {
    if (grupo.tipo === 'bloco') {
      const bloco = blocos[contaBlocos++]
      if (bloco.estatisticas && (bloco.estatisticas.sem.length || bloco.estatisticas.varias.length)) marcados.push(`bloco-${bloco.numero}`)
      for (const indice of grupo.versoes) if (avisosDoItem.has(indice)) marcados.push(`item-${itens[indice].id}`)
    } else if (avisosDoItem.has(grupo.indice)) {
      marcados.push(`item-${itens[grupo.indice].id}`)
    }
  }
  const versoesDoTexto = new Set(resultado?.versoes.map((v) => v.condicao))
  const cobertura = contaCom
    ? {
        conferidos: Object.keys(resultado.versoes_por_municipio).length,
        comErro: Object.keys(resultado.erros).length,
        ausentes: resultado.ausentes ?? [],
        blocosSemTexto: blocos.filter((b) => b.estatisticas.sem.length).map((b) => b.numero),
      }
    : null
  if (cobertura) cobertura.completa = !cobertura.comErro && !cobertura.ausentes.length

  // "Próximo aviso": o primeiro marcado abaixo do topo da área de leitura; no fim, volta
  // ao primeiro. O scroll-margin-top deixa o alvo logo abaixo do cabeçalho.
  // Se o último alvo ainda está no alto da tela, segue a lista a partir dele (sem isso,
  // o alvo que pousou um pouco abaixo do cabeçalho era escolhido de novo).
  const ultimoAviso = useRef(null)
  function proximoAviso() {
    const topo = cabecalho.current.getBoundingClientRect().bottom
    const alvos = marcados.map((id) => document.getElementById(id)).filter(Boolean)
    const ultimo = alvos.indexOf(document.getElementById(ultimoAviso.current))
    const noAlto = ultimo >= 0 && Math.abs(alvos[ultimo].getBoundingClientRect().top - topo) < 200
    const alvo = noAlto ? alvos[(ultimo + 1) % alvos.length] : alvos.find((e) => e.getBoundingClientRect().top > topo + 4) ?? alvos[0]
    if (!alvo) return
    ultimoAviso.current = alvo.id
    alvo.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const editou = temEdicao(itens)
  const opcoesDeCidade = useMemo(() => [...lugares, ...(csv?.so_no_csv ?? [])], [lugares, csv])
  let numeroBloco = 0
  const ultimoBloco = grupos.findLastIndex((g) => g.tipo === 'bloco')
  const docVazio = doc && !carregando && rascunho?.tipo !== 'doc_mudou' && textoSalvo.trim() === ''

  // O tutorial abre sozinho na primeira vez que um Doc abre: antes disso a tela só tem o
  // cabeçalho, e o tutorial não teria bloco nem painel para mostrar. Marca ao abrir, não ao
  // concluir: quem recarrega no meio não é surpreendido de novo (como no SAP-frontend).
  useEffect(() => {
    if (!doc || carregando || armazem.ler(CHAVE_TUTORIAL_VISTO)) return
    const espera = setTimeout(() => {
      armazem.gravar(CHAVE_TUTORIAL_VISTO, '1')
      // Sem localStorage não há como lembrar que já viu: melhor não abrir sozinho do que
      // abrir em toda visita. O botão continua funcionando.
      if (armazem.ler(CHAVE_TUTORIAL_VISTO)) abrirTutorial(u)
    }, 600)
    return () => clearTimeout(espera)
  }, [doc, carregando])
  useEffect(() => fecharTutorial, [])

  if (desligado) {
    return (
      <main>
        <div className="empty">
          <h2>O TemaLab não está ligado neste ambiente</h2>
          <p>Ele só funciona onde a API roda com LABORATORIO_HABILITADO=1 (o gamma).</p>
        </div>
      </main>
    )
  }

  const rodando = conferencia && (conferencia.estado === 'na_fila' || conferencia.estado === 'rodando')

  return (
    <Unidade.Provider value={u}>
      <header ref={cabecalho}>
        {/* Três grupos (André, 03/11: botões "apinhados" junto da marca): marca; o tema, como
            título do documento aberto; status e ações à direita, com Conferir na ponta. */}
        <div className="hrow">
          <div className="marca">
            <span className="marca-simbolo" aria-hidden="true">¶</span>
            <span className="marca-nome"><h1>TemaLab</h1><span>Data Nordeste</span></span>
          </div>
          <div className="escolha-tema" data-tour="tema">
            <span id="rotulo-tema">Tema</span>
            <SeletorDeTema temas={temas && opcoesDeTema} tema={tema} escolher={abrirTema} desligado={!temas || carregando || rodando} />
          </div>
          <div className="escolha-tema" data-tour="unidade">
            <span id="rotulo-unidade">Unidade</span>
            <div className="unidade-seg" role="group" aria-labelledby="rotulo-unidade">
              {Object.values(UNIDADES).map((x) => (
                <button key={x.chave} type="button" aria-pressed={unidade === x.chave} disabled={!temas || carregando || rodando} onClick={() => trocarUnidade(x.chave)}>
                  {x.nome}
                </button>
              ))}
            </div>
          </div>
          <span className="spacer" />
          {doc && (
            <span className="status">
              <span>Doc aberto às <b>{dataHora(doc.aberto_em)}</b></span>
              <span>Dados de <b>{dataHora(temaAtual.snapshot_gerado_em)}</b>{csv && <> + <b>{csv.nome}</b></>}</span>
            </span>
          )}
          {/* Estado não tem CSV de fallback: o backend casa as linhas por nm_mun. */}
          {unidade === 'municipio' && <label className={`btn${!doc || rodando || lendoCsv ? ' desligado' : ''}`} title="Testar com um CSV de uma view que ainda não existe: as colunas dele entram por cima dos dados do tema">
            {lendoCsv ? 'lendo o CSV…' : csv ? 'trocar o CSV' : 'usar um CSV'}
            <input
              type="file"
              accept=".csv,.txt,text/csv"
              hidden
              disabled={!doc || rodando || lendoCsv}
              onChange={(e) => {
                usarCsv(e.target.files[0])
                e.target.value = '' // o mesmo arquivo de novo também dispara
              }}
            />
          </label>}
          <button className="btn pri" onClick={conferir} disabled={!doc || rodando}>Conferir</button>
        </div>
      </header>
      <main className={tema ? 'com-painel' : ''}>
        {/* Status e avisos em faixa própria, acima das duas colunas: dentro da coluna do
            texto, eles empurravam só ela e desalinhavam do painel da cidade (André, 03/11). */}
        <div className="mensagens">
        {erro && <div className="banner erro">{erro}</div>}
        {csv && (
          <div className="banner csv">
            <b>CSV {csv.nome}</b>: {csv.colunas_do_csv.length} {csv.colunas_do_csv.length === 1 ? 'coluna' : 'colunas'}{' '}
            ({csv.colunas_do_csv.slice(0, 8).map((c) => `$${c}`).join(', ')}{csv.colunas_do_csv.length > 8 ? ', …' : ''}) por cima dos dados
            do tema em {contar(csv.casados, u)}.
            {csv.so_no_csv.length > 0 && (
              <> {contar(csv.so_no_csv.length, u)} só no CSV, sem os outros dados do tema: <Nomes nomes={csv.so_no_csv.slice(0, MAX_NOMES)} total={csv.so_no_csv.length} />.</>
            )}{' '}
            <span className="muted">O CSV fica só nesta aba: recarregar a página tira ele.</span>{' '}
            <button className="btn sm" onClick={tirarCsv} disabled={rodando}>tirar o CSV</button>
          </div>
        )}
        {rascunho?.tipo === 'restaurado' && (
          <div className="banner atencao">
            Rascunho de <b>{dataHora(rascunho.salvo_em)}</b> restaurado (o Doc não mudou desde então).{' '}
            <button className="btn sm" onClick={descartarRascunho}>descartar o rascunho</button>
          </div>
        )}
        {rascunho?.tipo === 'doc_mudou' && (
          <div className="banner atencao">
            <b>O Doc mudou desde o seu rascunho de {dataHora(rascunho.salvo.salvo_em)}.</b>
            <div>
              Continuar o rascunho traz suas edições, mas sobre o texto antigo do Doc: o que mudou no Doc depois não aparece aqui.
              Abrir o Doc atual apaga o rascunho.
            </div>
            <div className="acoes">
              <button className="btn sm" onClick={() => { aplicarRascunho(rascunho.salvo); setRascunho({ tipo: 'antigo' }) }}>continuar o rascunho</button>
              <button className="btn sm" onClick={() => { armazem.apagar(chaveDoRascunho(tema, unidade)); setRascunho(null) }}>abrir o Doc atual</button>
            </div>
          </div>
        )}
        {rascunho?.tipo === 'antigo' && (
          <div className="banner atencao">
            Este rascunho foi feito sobre uma versão anterior do Doc: "alterado" compara com aquela versão. Confira no Doc antes de colar.{' '}
            <button className="btn sm" onClick={descartarRascunho}>descartar o rascunho</button>
          </div>
        )}
        </div>
        <div className="coluna-texto">
        {/* Sempre à vista: só depois de editar, o "copiar o Doc inteiro" não era achado (André, 03/11). */}
        {doc && rascunho?.tipo !== 'doc_mudou' && (
          <PainelExportar
            editou={editou}
            alterados={blocos.filter((b) => b.alterado).map((b) => b.numero)}
            conferencia={!resultado ? 'nunca' : conferenciaVelha ? 'velha' : 'ok'}
            nAvisos={marcados.length}
            copiarTudo={() => copiar(exportar(itens), 'tudo')}
            copiado={copiado === 'tudo'}
          />
        )}
        {paraCopiar !== null && <CopiarAMao texto={paraCopiar} fechar={() => setParaCopiar(null)} />}
        {resultado && contaCom && (
          <Avisos
            resultado={resultado}
            crusSoltos={resultado.campos_crus.filter((c) => !crusAchados.has(c.campo))}
            naoEntendidasSoltas={resultado.condicoes_nao_entendidas.filter((a) => !versoesDoTexto.has(a.split('\n')[0].trim()))}
          />
        )}
        {carregando && <div className="empty"><p>Abrindo o Doc…</p></div>}
        {!tema && !carregando && (
          <div className="empty">
            <h2>Escolha um tema</h2>
            <p>O TemaLab abre a versão mais recente do Doc e confere o texto contra os 2.074 municípios, os 9 estados do Nordeste ou as áreas de interesse, pelo mesmo código do relatório.</p>
          </div>
        )}
        {docVazio && (
          <div className="empty">
            <h2>O Doc deste tema está vazio</h2>
            <p>Comece com um bloco aqui. Depois, "copiar o Doc inteiro" leva o texto, já com descricao_tema = “ … ”@@, para colar no Doc.</p>
            <button className="btn pri" onClick={novoBloco} data-tour="comecar">+ começar com um bloco</button>
          </div>
        )}
        {grupos.map((grupo, i) => {
          // Chaves com prefixo: id de texto e id de versão são números da mesma sequência,
          // e "b-3" e "t-3" não podem colidir (o React reaproveitaria o cartão errado).
          if (grupo.tipo !== 'bloco') return <Texto key={`t-${itens[grupo.indice].id}`} item={itens[grupo.indice]} avisos={avisosDe(grupo.indice)} tema={tema} colunas={colunas} csv={csv} />
          const primeiro = itens[grupo.versoes[0]]
          const bloco = blocos[numeroBloco++]
          return (
            <React.Fragment key={`b-${primeiro.id}`}>
            <Bloco
              numero={bloco.numero}
              alterado={bloco.alterado}
              dica={bloco.dica}
              copiar={() => copiar(textoDoBloco(itens, grupo.versoes), `b-${primeiro.id}`)}
              copiado={copiado === `b-${primeiro.id}`}
              estatisticas={bloco.estatisticas}
              completo={cobertura?.completa}
              juntar={grupos[i - 1]?.tipo === 'bloco' ? () => juntarComOdeCima(primeiro.id) : null}
              novaVersao={() => novaVersao(itens[grupo.versoes.at(-1)].id)}
              versoes={grupo.versoes.map((indice, j) => {
                const k = posicao.get(indice)
                return (
                  <Versao
                    key={itens[indice].id}
                    item={itens[indice]}
                    contagem={contaCom && k !== undefined ? resultado.versoes[k].municipios : undefined}
                    avisos={avisosDe(indice)}
                    naCidade={naCidadeAtual && k !== undefined ? naCidadeAtual.versoes[k]?.[1] : undefined}
                    podeSeparar={j > 0}
                    acoes={acoesDaVersao(itens[indice].id)}
                    tema={tema}
                    colunas={colunas}
                    prefixo={prefixo}
                    csv={csv}
                  />
                )
              })}
            />
            {i === ultimoBloco && <button className="btn ghost sm novo-bloco" onClick={novoBloco}>+ novo bloco</button>}
            </React.Fragment>
          )
        })}
        {doc && (
          <BarraDaConferencia
            conferencia={conferencia}
            rodando={rodando}
            resultado={resultado}
            velha={conferenciaVelha}
            casa={casaComOTexto}
            cobertura={cobertura}
            nBlocos={blocos.length}
            nAvisos={marcados.length}
            proximo={proximoAviso}
            conferir={conferir}
          />
        )}
        </div>
        {tema && (
          <PainelCidade cidade={cidade} setCidade={setCidade} cidades={opcoesDeCidade} resultado={naCidade} atualizando={atualizandoPainel} erro={erroPainel} />
        )}
      </main>
      <button type="button" className="botao-tutorial" data-tour="tutorial" onClick={() => abrirTutorial(u)}>
        <span className="simbolo" aria-hidden="true">?</span>Tutorial
      </button>
    </Unidade.Provider>
  )
}
