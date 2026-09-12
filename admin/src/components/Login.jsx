import React, { useState } from 'react'

export default function Login({ aoEntrar, erro, carregando }) {
  const [nome, setNome] = useState('');
  const [senha, setSenha] = useState('');

  return (
    <div className="tela-login">
      <form
        className="cartao-login"
        onSubmit={(e) => { e.preventDefault(); aoEntrar(nome, senha); }}
      >
        <p className="marca">Data Nordeste</p>
        <h1>Painel Editorial</h1>
        <p className="sub">
          Autoria dos relatórios municipais. Quem entra aqui edita e publica — não há
          níveis de acesso.
        </p>

        <label>
          <span>Seu nome</span>
          <input
            type="text" value={nome} autoFocus autoComplete="name"
            onChange={(e) => setNome(e.target.value)}
            placeholder="Como deve aparecer no histórico"
          />
        </label>

        <label>
          <span>Senha do painel</span>
          <input
            type="password" value={senha} autoComplete="current-password"
            onChange={(e) => setSenha(e.target.value)}
          />
        </label>

        {erro && <p className="erro">{erro}</p>}

        <button type="submit" disabled={carregando || !nome.trim() || !senha}>
          {carregando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
