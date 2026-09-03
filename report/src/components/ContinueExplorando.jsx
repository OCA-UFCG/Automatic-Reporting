import React from 'react';
import { QR_CODE_DATA_NORDESTE } from '../assets/qrCodeDataNordeste.js';

const LINK_DATA_NORDESTE = 'https://qr.codes/Bw7u3I';

export default function ContinueExplorando() {
  return (
    <section className="continue-explorando">
      <div className="continue-explorando-text">
        <p className="continue-explorando-title">Continue explorando</p>
        <p className="continue-explorando-body">
          Escaneie ou clique no QR code ao lado para conhecer mais conteúdos do Data Nordeste sobre este tema.
        </p>
      </div>
      <a
        className="continue-explorando-qr"
        href={LINK_DATA_NORDESTE}
        aria-label="Conheça mais conteúdos do Data Nordeste"
      >
        <img src={QR_CODE_DATA_NORDESTE} alt="QR code do Data Nordeste" width="96" height="96" />
      </a>
    </section>
  );
}
