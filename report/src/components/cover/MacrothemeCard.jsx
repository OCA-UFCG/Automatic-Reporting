import React from 'react';
import { MacrothemeIcon } from '../Brand.jsx';

export default function MacrothemeCard({ macrotema }) {
  const cardStyle = macrotema?.cor
    ? { '--macrotheme-color': macrotema.cor }
    : undefined;
  return (
    <div className="macrotheme-card" style={cardStyle}>
      <div className="macrotheme-card-left">
        <span className="macrotheme-icon-box" aria-hidden="true">
          <MacrothemeIcon icone={macrotema.icone} color={macrotema.cor} />
        </span>
        <span className="macrotheme-name">{macrotema.nome}</span>
      </div>
    </div>
  );
}
