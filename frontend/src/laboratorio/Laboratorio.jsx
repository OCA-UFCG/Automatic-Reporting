import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  OPERADORES,
  agruparEmBlocos,
  avisosDaVersao,
  blocoAlterado,
  camposDaCondicao,
  chaveDoRascunho,
  condicaoDoItem,
  doRascunho,
  exportar,
  fraseDaCondicao,
  lerDoc,
  numeroValido,
  paraRascunho,
  prefixoDoDoc,
  temEdicao,
  textoDoBloco,
  textoDoItem,
  trechoParaLer,
} from './modelo.js'

// Em produção, sempre a mesma origem: atrás do gamma-lab.oca-portal.com, o basic auth
// do nginx cobre a página e a API juntas. O build do gamma grava um VITE_API_BASE_URL
// (o do gerador, outro endereço), que mandaria a API para fora do basic auth. Só no dev
// do Vite, que roda noutra porta, ele vale.
const API_BASE = import.meta.env.DEV ? import.meta.env.VITE_API_BASE_URL || '' : ''
const INTERVALO_MS = 1000
const MAX_NOMES = 8
const MAX_SUGESTOES = 12

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
const municipios = (n) => `${numero(n)} ${n === 1 ? 'município' : 'municípios'}`

// Só para a tela: várias linhas em branco seguidas viram uma. A exportação usa o original.
const paraTela = (texto) => texto.trim().replace(/\n\s*\n(\s*\n)+/g, '\n\n')

// Coluna de texto com 2 a 40 valores, fora a sigla da UF: as que o "ler com cada valor"
// do backend lê (services/laboratorio.py, _FORA_DO_LER_COM_CADA_VALOR).
const comparavel = (info) =>
  info?.tipo === 'texto' && info.distintos >= 2 && info.distintos <= 40 && info.coluna !== 'sigla_uf'

function resumoDaColuna(info) {
  // Pode ser apelido que o gerador resolve (_resolver_campo_com_alias): quem diz se
  // sai cru é a conferência.
  if (!info) return 'não está nas colunas deste tema (se a conferência não acusar, é um apelido)'
  const vazios = info.vazios ? ` · vazia em ${municipios(info.vazios)}` : ''
  if (info.tipo === 'numero') {
    const outros = info.nao_numeros.map((v) => `"${v.valor}" em ${numero(v.municipios)}`).join(', ')
    return `número de ${numero(info.min)} a ${numero(info.max)} · zero em ${municipios(info.zeros)}${vazios}${outros ? ` · ${outros}` : ''}`
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
function tituloDaColuna(nome, info) {
  const { valores, mais } = valoresDaColuna(info)
  const linhas = valores.map((v) => `• ${v.valor} (${numero(v.municipios)})`)
  if (mais) linhas.push(`… e mais ${numero(mais)} valores`)
  return [`$${nome}: ${resumoDaColuna(info)}`, ...linhas].join('\n')
}

function FichaDaColuna({ nome, info }) {
  const { valores, mais } = valoresDaColuna(info)
  return (
    <div className="ficha">
      <b>${nome}</b> <span className="muted">{resumoDaColuna(info)}</span>
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
  if (!colunas) return texto
  return texto.split(/((?:[A-Za-z_][\w-]*\.)?\$[A-Za-z_]\w*)/).map((parte, i) => {
    if (i % 2 === 0) return parte
    const nome = parte.slice(parte.indexOf('$') + 1)
    const info = colunas.get(nome)
    return <span key={i} className={`campo${info ? '' : ' desconhecido'}`} title={tituloDaColuna(nome, info)}>{parte}</span>
  })
}

// Textarea com autocomplete de $coluna: abre ao digitar "$" (com ou sem "tema.") e
// troca só o nome depois do "$". A lista fica embaixo do textarea, não no cursor.
function EditorComColunas({ valor, mudar, colunas }) {
  const ref = useRef(null)
  const cursor = useRef(null)
  const [sugestao, setSugestao] = useState(null)
  useEffect(() => {
    if (cursor.current === null) return
    ref.current.setSelectionRange(cursor.current, cursor.current)
    cursor.current = null
  })
  // A condição mudou (ex.: "trocar a 1ª linha"): mostra o topo, onde ela está.
  const primeiraLinha = valor.split('\n')[0]
  useEffect(() => {
    ref.current.scrollTop = 0
  }, [primeiraLinha])

  function atualizar(alvo) {
    const pos = alvo.selectionStart
    const m = alvo.value.slice(0, pos).match(/\$(\w*)$/)
    if (!m || !colunas) return setSugestao(null)
    const q = m[1].toLowerCase()
    const nomes = [...colunas.keys()]
    const lista = [
      ...nomes.filter((c) => c.toLowerCase().startsWith(q)),
      ...nomes.filter((c) => !c.toLowerCase().startsWith(q) && c.toLowerCase().includes(q)),
    ].slice(0, MAX_SUGESTOES)
    if (!lista.length || (lista.length === 1 && lista[0].toLowerCase() === q)) return setSugestao(null)
    setSugestao({ inicio: pos - m[1].length, fim: pos, lista, sel: 0 })
  }
  function escolher(nome) {
    cursor.current = sugestao.inicio + nome.length
    mudar(valor.slice(0, sugestao.inicio) + nome + valor.slice(sugestao.fim))
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
        rows={Math.max(4, valor.split('\n').length + 1)}
        autoFocus
        onChange={(e) => {
          mudar(e.target.value)
          atualizar(e.target)
        }}
        onKeyDown={tecla}
        onKeyUp={(e) => ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key) && atualizar(e.target)}
        onClick={(e) => atualizar(e.target)}
        onBlur={() => setSugestao(null)}
      />
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
function FormCondicao({ colunas, prefixo, escrever, fechar }) {
  const [coluna, setColuna] = useState('')
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
        <input list="lista-colunas" placeholder="coluna" value={coluna} onChange={(e) => setColuna(e.target.value.replace(/^.*\$/, '').trim())} />
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
function LerComCadaValor({ tema, texto, colunas }) {
  const trecho = trechoParaLer(texto)
  const [lido, setLido] = useState(null)
  const usadas = [...camposDaCondicao(trecho)].filter((c) => comparavel(colunas?.get(c)))
  if (!usadas.length) return null
  const atual = lido?.trecho === trecho ? lido : null // texto editado: a leitura antiga não vale

  async function ler() {
    setLido({ trecho, carregando: true })
    try {
      setLido({ trecho, ...(await postarJson(`/laboratorio/${tema}/cada-valor`, { texto: trecho })) })
    } catch (err) {
      setLido({ trecho, erro: err.message })
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
                  {municipios(v.municipios)}{v.vale_em < v.municipios ? `, o trecho sai em ${numero(v.vale_em)}` : ''}
                </span>
              </div>
              {v.texto ? (
                <div className="exemplo"><span className="muted">{v.cidade}:</span> {comDestaque(v.texto, v.valor)}</div>
              ) : (
                <div className="muted">Com este valor, o trecho não sai em nenhum município.</div>
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

function Versao({ item, contagem, naCidade, podeSeparar, acoes, tema, colunas, prefixo }) {
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
  function salvar() {
    const { antes, depois } = separarEspacos(texto)
    acoes.salvar(antes + rascunho.trim() + (depois || '\n'))
    setEditando(false)
  }

  if (editando) {
    return (
      <div className="versao editando">
        <EditorComColunas valor={rascunho} mudar={setRascunho} colunas={colunas} />
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
          {removida ? item.condicao : condicao ? <ComCampos texto={condicao} colunas={colunas} /> : 'A 1ª linha não é mais uma condição: o gerador vai ler isto como texto fixo'}
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
      {!removida && <div className="corpo"><ComCampos texto={paraTela(corpo)} colunas={colunas} /></div>}
      {!removida && <LerComCadaValor tema={tema} texto={texto} colunas={colunas} />}
    </div>
  )
}

function Texto({ item, tema, colunas }) {
  return (
    <div className="card texto">
      <div className="cbody"><ComCampos texto={paraTela(textoDoItem(item))} colunas={colunas} /></div>
      <LerComCadaValor tema={tema} texto={textoDoItem(item)} colunas={colunas} />
    </div>
  )
}

function Bloco({ numero: n, versoes, estatisticas, juntar, novaVersao, alterado, avisos, copiar, copiado }) {
  return (
    <div className="card" id={`bloco-${n}`}>
      <div className="chead">
        <span className="ctag">Bloco {n}</span>
        <span className="muted">{versoes.length} {versoes.length === 1 ? 'versão' : 'versões'}</span>
        <span className={`chip ${alterado ? 'atencao' : ''}`}>{alterado ? 'alterado' : 'igual ao Doc'}</span>
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
        <button className={`btn sm${alterado ? ' pri' : ''}`} onClick={copiar} title="Copia o bloco para colar no Doc, por cima do mesmo trecho">
          {copiado ? 'copiado ✓' : 'copiar bloco'}
        </button>
      </div>
      {avisos.length > 0 && (
        <div className="bloco-detalhe avisos">
          {avisos.map((a) => <div key={a}>⚠ {a}</div>)}
        </div>
      )}
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

// Resumo para levar ao Doc (spec, "Exportar"): copiar por bloco é o caminho
// principal; copiar o tema inteiro é o secundário, porque colar o Doc inteiro apaga
// comentários e formatação que o editorial tenha nele.
function PainelExportar({ alterados, conferencia, avisosLocais, copiarTudo, copiado }) {
  return (
    <div className="card exportar">
      <div className="chead"><span className="ctag">Para levar ao Doc</span></div>
      <div className="cbody">
        <div>
          {alterados.length
            ? <>Blocos alterados: {alterados.map((n, i) => <span key={n}>{i ? ', ' : ''}<a href={`#bloco-${n}`}>Bloco {n}</a></span>)}. Copie cada um e cole no Doc por cima do mesmo trecho.</>
            : 'Nenhum bloco alterado: as mudanças estão em texto fora dos blocos.'}
        </div>
        <div className={conferencia === 'ok' ? 'muted' : 'aviso-exportar'}>
          {conferencia === 'ok' && '✓ Conferido depois da última mudança (os avisos do gerador, se houver, estão acima).'}
          {conferencia === 'velha' && '⚠ O texto mudou desde a última conferência: clique em Conferir antes de colar.'}
          {conferencia === 'nunca' && '⚠ Ainda não conferido: clique em Conferir antes de colar.'}
        </div>
        {avisosLocais > 0 && <div className="aviso-exportar">⚠ {avisosLocais === 1 ? '1 aviso' : `${avisosLocais} avisos`} nos blocos (veja em cada bloco).</div>}
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
        <textarea readOnly value={texto} autoFocus onFocus={(e) => e.target.select()} />
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
  const [colunas, setColunas] = useState(null)
  const [rascunho, setRascunho] = useState(null) // {tipo: restaurado | doc_mudou | antigo, ...}
  const [hashBase, setHashBase] = useState(null) // hash do Doc em que o texto da tela se baseia
  const [copiado, setCopiado] = useState(null)
  const [paraCopiar, setParaCopiar] = useState(null)
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
    setColunas(null)
    setRascunho(null)
    if (!slug) return
    // Em paralelo com o Doc: sem as colunas, a tela funciona, só sem a ajuda.
    pedir(`/laboratorio/${slug}/colunas`)
      .then((r) => temaVivo.current === slug && setColunas(new Map(r.colunas.map((c) => [c.coluna, c]))))
      .catch((err) => temaVivo.current === slug && setErro(`Colunas do tema: ${err.message}`))
    setCarregando(true)
    try {
      const aberto = await pedir(`/laboratorio/${slug}/doc`)
      setDoc({ ...aberto, aberto_em: new Date().toISOString() })
      const lidos = lerDoc(aberto.texto)
      proximoId.current = lidos.length
      setItens(lidos)
      setHashBase(aberto.hash)
      const salvo = doRascunho(armazem.ler(chaveDoRascunho(slug)) ?? '')
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

  function aplicarRascunho(salvo) {
    setItens(salvo.itens)
    setAjustes(salvo.ajustes)
    proximoId.current = salvo.proximoId
    setHashBase(salvo.hash)
  }
  function descartarRascunho() {
    if (!window.confirm('Descartar o rascunho? As edições somem e o texto volta ao Doc atual.')) return
    armazem.apagar(chaveDoRascunho(tema))
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
      armazem.gravar(chaveDoRascunho(tema), paraRascunho({ hash: hashBase, itens, ajustes, proximoId: proximoId.current }))
    } else {
      armazem.apagar(chaveDoRascunho(tema))
    }
  }, [itens, ajustes])

  async function copiar(texto, rotulo) {
    try {
      await navigator.clipboard.writeText(texto)
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
  const conferenciaVelha = resultado && textoConferido !== exportar(itens)
  const temaAtual = temas?.find((t) => t.slug === tema)
  const blocos = grupos.filter((g) => g.tipo === 'bloco').map((g, i) => ({
    ...g,
    numero: i + 1,
    alterado: blocoAlterado(itens, g.versoes),
    avisos: g.versoes.flatMap((indice) => avisosDaVersao(itens[indice], colunas)),
  }))
  const editou = temEdicao(itens)
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
          <datalist id="lista-colunas">{colunas && [...colunas.keys()].map((c) => <option key={c} value={c} />)}</datalist>
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
              <button className="btn sm" onClick={() => { armazem.apagar(chaveDoRascunho(tema)); setRascunho(null) }}>abrir o Doc atual</button>
            </div>
          </div>
        )}
        {rascunho?.tipo === 'antigo' && (
          <div className="banner atencao">
            Este rascunho foi feito sobre uma versão anterior do Doc: "alterado" compara com aquela versão. Confira no Doc antes de colar.{' '}
            <button className="btn sm" onClick={descartarRascunho}>descartar o rascunho</button>
          </div>
        )}
        {editou && rascunho?.tipo !== 'doc_mudou' && (
          <PainelExportar
            alterados={blocos.filter((b) => b.alterado).map((b) => b.numero)}
            conferencia={!resultado ? 'nunca' : conferenciaVelha ? 'velha' : 'ok'}
            avisosLocais={blocos.reduce((n, b) => n + b.avisos.length, 0)}
            copiarTudo={() => copiar(exportar(itens), 'tudo')}
            copiado={copiado === 'tudo'}
          />
        )}
        {paraCopiar !== null && <CopiarAMao texto={paraCopiar} fechar={() => setParaCopiar(null)} />}
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
          if (grupo.tipo !== 'bloco') return <Texto key={`t-${itens[grupo.indice].id}`} item={itens[grupo.indice]} tema={tema} colunas={colunas} />
          const posicoes = grupo.versoes.map((indice) => posicao.get(indice)).filter((k) => k !== undefined)
          const contaCom = casaComOTexto && !conferenciaVelha
          const primeiro = itens[grupo.versoes[0]]
          const bloco = blocos[numeroBloco++]
          return (
            <Bloco
              key={`b-${primeiro.id}`}
              numero={bloco.numero}
              alterado={bloco.alterado}
              avisos={bloco.avisos}
              copiar={() => copiar(textoDoBloco(itens, grupo.versoes), `b-${primeiro.id}`)}
              copiado={copiado === `b-${primeiro.id}`}
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
                    tema={tema}
                    colunas={colunas}
                    prefixo={prefixo}
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
