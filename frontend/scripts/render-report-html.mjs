import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createRequire } from 'node:module'
import { build } from 'esbuild'

async function readStdin() {
  const chunks = []

  for await (const chunk of process.stdin) {
    chunks.push(chunk)
  }

  return Buffer.concat(chunks).toString('utf8')
}

const input = JSON.parse(await readStdin())
input.reportCss = input.reportCssPath
  ? await readFile(input.reportCssPath, 'utf8')
  : input.reportCss ?? ''

const bundle = await build({
  absWorkingDir: new URL('..', import.meta.url).pathname,
  bundle: true,
  entryPoints: ['src/report/render-entry.jsx'],
  format: 'cjs',
  platform: 'node',
  write: false,
  jsx: 'automatic',
})

const tempDir = await mkdtemp(join(tmpdir(), 'report-render-'))
const tempModulePath = join(tempDir, 'render-entry.cjs')
await writeFile(tempModulePath, bundle.outputFiles[0].text, 'utf8')

const require = createRequire(import.meta.url)
const { renderReportHtml } = require(tempModulePath)

process.stdout.write(renderReportHtml(input))
