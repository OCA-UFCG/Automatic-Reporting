// Tutorial da tela (André, 09/11/2026: "como acontece no SAP-frontend"). Mesmo
// driver.js e o mesmo jeito do usePlatformTour do SAP: abre sozinho na primeira vez
// e o botão "Tutorial", no canto, abre de novo.
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import './tutorial.css'

// Trocar o sufixo faz todo mundo ver de novo: útil se o tutorial mudar bastante.
export const CHAVE_TUTORIAL_VISTO = 'temalab:tutorial:v1:visto'

// Os passos dependem do que está na tela: sem tema não há bloco nem painel, e um Doc
// vazio não tem bloco. Passo cujo alvo não está na tela fica de fora, para o balão não
// abrir no meio da tela apontando para nada.
function passos(u) {
  return [
    {
      popover: {
        title: 'Bem-vindo ao TemaLab',
        description:
          'Aqui você escreve o texto de um tema e vê, antes de levar ao Doc, como ele sai em cada lugar. São poucos passos.',
      },
    },
    {
      element: '[data-tour="tema"]',
      popover: {
        title: 'O tema',
        description:
          'O TemaLab abre a versão mais recente do Google Doc do tema. Nada aqui muda o Doc: no fim, você copia o texto e cola lá.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '[data-tour="unidade"]',
      popover: {
        title: 'Município, estado ou área',
        description:
          'Cada unidade tem um Doc próprio. O texto é conferido contra os 2.074 municípios, os 9 estados do Nordeste ou as áreas de interesse.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '[data-tour="comecar"]',
      popover: {
        title: 'Doc vazio',
        description: 'Este Doc ainda não tem texto. Comece com um bloco: ele já vem com um modelo de versão para trocar.',
        side: 'top', align: 'center',
      },
    },
    {
      element: '[id^="bloco-"]',
      popover: {
        title: 'Blocos e versões',
        description:
          `Cada bloco é um trecho do relatório. Uma versão com "Para quando…" só sai onde a condição vale, e cada $campo vira o número de cada ${u.um}. Passe o mouse numa versão para editar.`,
        side: 'right', align: 'start',
      },
    },
    {
      element: '.painel',
      popover: {
        title: 'O texto pronto',
        description: `Escolha ${u.um === 'área' ? 'uma' : 'um'} ${u.um} aqui e veja o tema como sai no relatório. Ele acompanha o que você escreve, sem precisar salvar.`,
        side: 'left', align: 'start',
      },
    },
    {
      element: '.barra-conferencia',
      popover: {
        title: 'Conferir',
        description:
          `Roda o texto em ${u.todos} ${u.varios} pelo mesmo código do relatório. Avisa onde um bloco fica sem texto, sai repetido ou deixa um $campo cru. "Próximo aviso" leva a cada trecho marcado em vermelho.`,
        side: 'top', align: 'start',
      },
    },
    {
      element: '.exportar',
      popover: {
        title: 'Levar ao Doc',
        description:
          'Cada bloco tem o seu "copiar", para colar no lugar dele no Doc. O que você edita fica guardado neste navegador como rascunho até lá.',
        side: 'bottom', align: 'start',
      },
    },
    {
      element: '[data-tour="tutorial"]',
      popover: {
        title: 'Para ver de novo',
        description: 'O tutorial fica neste botão.',
        side: 'top', align: 'end',
      },
    },
  ].filter((p) => !p.element || document.querySelector(p.element))
}

// Troca o "3/7" por uma fileira de pontos, com o passo atual alongado (como no SAP). O
// texto fica escondido da vista, para leitor de tela.
function pontosDeProgresso(dom, { config, state }) {
  const total = config.steps?.length ?? 0
  const atual = state.activeIndex
  if (atual === undefined || !total) return
  const rotulo = document.createElement('span')
  rotulo.className = 'temalab-tour-sr'
  rotulo.textContent = dom.progress.textContent
  const pontos = document.createElement('span')
  pontos.className = 'temalab-tour-pontos'
  pontos.setAttribute('aria-hidden', 'true')
  for (let i = 0; i < total; i++) {
    const ponto = document.createElement('span')
    ponto.className = i === atual ? 'atual' : i < atual ? 'feito' : ''
    pontos.append(ponto)
  }
  dom.progress.replaceChildren(rotulo, pontos)
}

let aberto = null

export function abrirTutorial(u) {
  aberto?.destroy()
  aberto = driver({
    steps: passos(u),
    showProgress: true,
    progressText: '{{current}} de {{total}}',
    nextBtnText: 'Próximo',
    prevBtnText: 'Voltar',
    doneBtnText: 'Pronto',
    popoverClass: 'temalab-tour',
    onPopoverRender: pontosDeProgresso,
    // Um clique sem querer fora do balão não fecha; para sair há o ×, o Esc e o "Pronto".
    overlayClickBehavior: 'none',
    // Clicar no que está em destaque (Conferir, editar) no meio do tutorial mudaria a tela
    // por trás do balão.
    disableActiveInteraction: true,
    overlayColor: '#003616',
    overlayOpacity: 0.55,
    stagePadding: 6,
    stageRadius: 6,
    popoverOffset: 14,
  })
  aberto.drive()
}

export function fecharTutorial() {
  aberto?.destroy()
  aberto = null
}
