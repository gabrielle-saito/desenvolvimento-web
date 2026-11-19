import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router";

import { api, errosPorCampo, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Campo from "../componentes/Campo.jsx";
import CampoSenha from "../componentes/CampoSenha.jsx";
import LayoutAcesso from "../componentes/LayoutAcesso.jsx";
import { useAuth } from "../contexto/AuthContext.jsx";
import { useTitulo } from "../util/useCarregar.js";

const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Cadastro público: a conta nasce como colaborador (a API não aceita outro
// papel aqui). Promover alguém é tarefa do admin.
export default function Cadastro() {
  useTitulo("Criar conta");
  const { usuario } = useAuth();
  const navigate = useNavigate();
  const [campos, setCampos] = useState({ nome: "", email: "", senha: "", confirmacao: "" });
  const [erros, setErros] = useState({});
  const [aviso, setAviso] = useState(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to="/agenda" replace />;

  const mudar = (evento) => setCampos((c) => ({ ...c, [evento.target.name]: evento.target.value }));

  function validar() {
    const e = {};
    if (!campos.nome.trim()) e.nome = "Informe o seu nome.";
    if (!EMAIL_VALIDO.test(campos.email.trim())) e.email = "Informe um e-mail válido.";
    if (campos.senha.length < 8) e.senha = "A senha precisa ter pelo menos 8 caracteres.";
    if (campos.confirmacao !== campos.senha) e.confirmacao = "As senhas não são iguais.";
    return e;
  }

  async function enviar(evento) {
    evento.preventDefault();
    const encontrados = validar();
    setErros(encontrados);
    if (Object.keys(encontrados).length) return;

    setEnviando(true);
    setAviso(null);
    try {
      const email = campos.email.trim();
      await api.post("/v1/auth/registro", { nome: campos.nome.trim(), email, senha: campos.senha });
      navigate("/login", { state: { cadastrou: true, email: email.toLowerCase() } });
    } catch (erro) {
      setErros(errosPorCampo(erro));
      setAviso({ texto: erro.status === 409 ? "Este e-mail já tem cadastro. Entre com ele ou use outro." : mensagemDeErro(erro), tipo: "erro" });
      setEnviando(false);
    }
  }

  return (
    <LayoutAcesso>
      <h1>Criar conta</h1>
      <p className="discreto">Para reservar salas e ver a agenda da empresa.</p>
      <Aviso aviso={aviso} />
      <form onSubmit={enviar} noValidate>
        <Campo id="nome" name="nome" rotulo="Nome" autoComplete="name" maxLength={120} autoFocus value={campos.nome} onChange={mudar} erro={erros.nome} />
        <Campo id="email" name="email" rotulo="E-mail" type="email" autoComplete="email" placeholder="nome@veritas.com.br" value={campos.email} onChange={mudar} erro={erros.email} />
        <CampoSenha id="senha" name="senha" autoComplete="new-password" maxLength={128} value={campos.senha} onChange={mudar} erro={erros.senha} />
        <CampoSenha id="confirmacao" name="confirmacao" rotulo="Repita a senha" autoComplete="new-password" value={campos.confirmacao} onChange={mudar} erro={erros.confirmacao} />
        <button type="submit" className="primario largo" disabled={enviando}>
          {enviando ? "Criando conta…" : "Criar conta"}
        </button>
      </form>
      <p className="login-ajuda">
        Já tem conta? <Link to="/login">Entrar</Link>
      </p>
    </LayoutAcesso>
  );
}
