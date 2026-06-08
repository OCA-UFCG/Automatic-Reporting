import React from 'react';
import { MacrothemeIcon } from '../Brand.jsx';

export default function MacrothemeCard({ macrotema }) {
  return (
    <div className="macrotheme-card">
      <span className="macrotheme-icon-box" aria-hidden="true">
        <MacrothemeIcon icone={macrotema.icone} />
      </span>
      <span className="macrotheme-name">{macrotema.nome}</span>
    </div>
  );
}
