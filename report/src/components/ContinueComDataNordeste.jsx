import React from 'react';
import { QR_CODE_CATALOGO_DADOS } from '../assets/qrCodeCatalogoDados.js';
import { QR_CODE_MONTE_RELATORIO } from '../assets/qrCodeMonteRelatorio.js';

const LINK_CATALOGO_DADOS = 'https://datanordeste.sudene.gov.br/catalog';
const LINK_MONTE_RELATORIO = 'https://datanordeste.sudene.gov.br/reports';

function IconCatalogoDados() {
  return (
    <svg className="continue-cta-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        fill="#018F39"
        d="M10 7.52083C11.1944 7.52083 12.4271 7.34028 13.6979 6.97917C14.9687 6.61806 15.6806 6.24306 15.8333 5.85417C15.6806 5.45139 14.9826 5.06944 13.7396 4.70833C12.4965 4.34722 11.25 4.16667 10 4.16667C8.73611 4.16667 7.49653 4.34375 6.28125 4.69792C5.06597 5.05208 4.36111 5.4375 4.16667 5.85417C4.375 6.25694 5.10069 6.63542 6.34375 6.98958C7.58681 7.34375 8.80555 7.52083 10 7.52083ZM8.72917 15.7708C8.86805 16.0903 9.02778 16.3958 9.20833 16.6875C9.38889 16.9792 9.59722 17.25 9.83333 17.5C8.81944 17.4861 7.86458 17.3924 6.96875 17.2187C6.07292 17.0451 5.29514 16.809 4.63542 16.5104C3.97569 16.2118 3.45486 15.8611 3.07292 15.4583C2.69097 15.0556 2.5 14.625 2.5 14.1667V5.83333C2.5 5.375 2.69792 4.94444 3.09375 4.54167C3.48958 4.13889 4.02778 3.78472 4.70833 3.47917C5.38889 3.17361 6.18403 2.93403 7.09375 2.76042C8.00347 2.58681 8.97222 2.5 10 2.5C11.0278 2.5 11.9965 2.58681 12.9062 2.76042C13.816 2.93403 14.6111 3.17361 15.2917 3.47917C15.9722 3.78472 16.5104 4.13889 16.9062 4.54167C17.3021 4.94444 17.5 5.375 17.5 5.83333C17.5 6.29167 17.3021 6.72222 16.9062 7.125C16.5104 7.52778 15.9722 7.88194 15.2917 8.1875C14.6111 8.49305 13.816 8.73264 12.9062 8.90625C11.9965 9.07986 11.0278 9.16667 10 9.16667C8.81944 9.16667 7.72917 9.0625 6.72917 8.85417C5.72917 8.64583 4.875 8.34028 4.16667 7.9375V10.0417C4.72222 10.5556 5.41667 10.9306 6.25 11.1667C7.08333 11.4028 7.92361 11.5556 8.77083 11.625C8.65972 11.8333 8.56944 12.0729 8.5 12.3437C8.43055 12.6146 8.38194 12.9167 8.35417 13.25C7.52083 13.1528 6.74653 13.0139 6.03125 12.8333C5.31597 12.6528 4.69444 12.4097 4.16667 12.1042V14.1667C4.36111 14.5139 4.89583 14.8403 5.77083 15.1458C6.64583 15.4514 7.63194 15.6597 8.72917 15.7708ZM18 19.1667L15.75 16.9167C15.4444 17.0972 15.125 17.2396 14.7917 17.3437C14.4583 17.4479 14.1111 17.5 13.75 17.5C12.7083 17.5 11.8229 17.1354 11.0937 16.4062C10.3646 15.6771 10 14.7917 10 13.75C10 12.7083 10.3646 11.8229 11.0937 11.0937C11.8229 10.3646 12.7083 10 13.75 10C14.7917 10 15.6771 10.3646 16.4062 11.0937C17.1354 11.8229 17.5 12.7083 17.5 13.75C17.5 14.1111 17.4479 14.4583 17.3437 14.7917C17.2396 15.125 17.0972 15.4444 16.9167 15.75L19.1667 18L18 19.1667ZM13.75 15.8333C14.3333 15.8333 14.8264 15.6319 15.2292 15.2292C15.6319 14.8264 15.8333 14.3333 15.8333 13.75C15.8333 13.1667 15.6319 12.6736 15.2292 12.2708C14.8264 11.8681 14.3333 11.6667 13.75 11.6667C13.1667 11.6667 12.6736 11.8681 12.2708 12.2708C11.8681 12.6736 11.6667 13.1667 11.6667 13.75C11.6667 14.3333 11.8681 14.8264 12.2708 15.2292C12.6736 15.6319 13.1667 15.8333 13.75 15.8333Z"
      />
    </svg>
  );
}

function IconMonteRelatorio() {
  return (
    <svg className="continue-cta-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        fill="#018F39"
        d="M8.33333 11.6667H11.6667V10H8.33333V11.6667ZM8.33333 9.16667H15V7.5H8.33333V9.16667ZM8.33333 6.66667H15V5H8.33333V6.66667ZM6.66667 15C6.20833 15 5.81611 14.8369 5.49 14.5108C5.16333 14.1842 5 13.7917 5 13.3333V3.33333C5 2.875 5.16333 2.4825 5.49 2.15583C5.81611 1.82972 6.20833 1.66667 6.66667 1.66667H16.6667C17.125 1.66667 17.5175 1.82972 17.8442 2.15583C18.1703 2.4825 18.3333 2.875 18.3333 3.33333V13.3333C18.3333 13.7917 18.1703 14.1842 17.8442 14.5108C17.5175 14.8369 17.125 15 16.6667 15H6.66667ZM6.66667 13.3333H16.6667V3.33333H6.66667V13.3333ZM3.33333 18.3333C2.875 18.3333 2.48278 18.1703 2.15667 17.8442C1.83 17.5175 1.66667 17.125 1.66667 16.6667V5H3.33333V16.6667H15V18.3333H3.33333Z"
      />
    </svg>
  );
}

function ContinueCtaCard({ icon, titulo, descricao, texto_botao, href, qrCode, qrAlt }) {
  return (
    <div className="continue-cta-card">
      <div className="continue-cta-icon-wrap">{icon}</div>
      <p className="continue-cta-title">{titulo}</p>
      <p className="continue-cta-description">{descricao}</p>
      <div className="continue-cta-qr">
        <img src={qrCode} alt={qrAlt} width="109" height="109" />
      </div>
      <a className="continue-cta-button" href={href}>
        {texto_botao}
      </a>
    </div>
  );
}

export default function ContinueComDataNordeste() {
  return (
    <div className="continue-cta-wrap">
      <section className="continue-cta">
        <div className="continue-cta-header">
          <p className="continue-cta-heading">
            Continue com o <span className="continue-cta-heading-highlight">Data Nordeste</span>
          </p>
          <p className="continue-cta-subtitle">
            Explore mais dados ou monte o seu próprio relatório personalizado
          </p>
        </div>
        <div className="continue-cta-grid">
          <ContinueCtaCard
            icon={<IconCatalogoDados />}
            titulo="Catálogo de dados"
            descricao="Explore todos os indicadores e bases usadas neste painel"
            texto_botao="Acessar catálogo"
            href={LINK_CATALOGO_DADOS}
            qrCode={QR_CODE_CATALOGO_DADOS}
            qrAlt="QR code do catálogo de dados"
          />
          <ContinueCtaCard
            icon={<IconMonteRelatorio />}
            titulo="Monte seu relatório"
            descricao="Escolha o município e gere um relatório como este"
            texto_botao="Criar relatório"
            href={LINK_MONTE_RELATORIO}
            qrCode={QR_CODE_MONTE_RELATORIO}
            qrAlt="QR code para montar seu relatório"
          />
        </div>
      </section>
    </div>
  );
}
