import { BrandMark } from './BrandMark.jsx'

export function PdfHeader() {
  return (
    <div className="pdf-page-header">
      <div className="pdf-page-header-brand">
        <BrandMark />
      </div>
      <span className="pdf-page-header-subtitle">Relatorio automatico</span>
    </div>
  )
}
