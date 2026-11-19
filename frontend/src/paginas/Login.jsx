import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router";

import { ErroApi, mensagemDeErro } from "../api/cliente.js";
import Aviso from "../componentes/Aviso.jsx";
import Campo from "../componentes/Campo.jsx";
import CampoSenha from "../componentes/CampoSenha.jsx";
import LayoutAcesso from "../componentes/LayoutAcesso.jsx";
import { useAuth } from "../contexto/AuthContext.jsx";
import { useTitulo } from "../util/useCarregar.js";

export default function Login() {
  useTitulo("Entrar");
  const { usuario, entrar } = useAuth();
  const navigate = useNavigate();
  const local = useLocation();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(local.state?.email ?? "");
  const [senha, setSenha] = useState("");
  const [erros, setErros] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState(() => {
    if (local.state?.cadastrou) return { texto: "Conta criada! Entre com o seu e-mail e a sua senha.", tipo: "sucesso" };
    if (params.has("expirou")) return { texto: "Sua sessão expirou. Entre novamente.", tipo: "info" };
    return null;
  });

  // Já está logado: não faz sentido ver o login.
  if (usuario) return <Navigate to="/agenda" replace />;

  async function enviar(evento) {
    evento.preventDefault();
    const faltando = {};
    if (!email.trim()) faltando.email = "Informe o e-mail.";
    if (!senha) faltando.senha = "Informe a senha.";
    setErros(faltando);
    if (Object.keys(faltando).length) return;

    setEnviando(true);
    setAviso(null);
    try {
      await entrar(email.trim(), senha);
      navigate(local.state?.voltarPara ?? "/agenda", { replace: true });
    } catch (erro) {
      const texto = erro instanceof ErroApi && erro.status === 401 ? "E-mail ou senha inválidos." : mensagemDeErro(erro);
      setAviso({ texto, tipo: "erro" });
      setEnviando(false);
    }
  }

  return (
    <LayoutAcesso>
      <h1>Entrar</h1>
      <p className="discreto">Use o e-mail e a senha da empresa.</p>
      <Aviso aviso={aviso} />
      <form onSubmit={enviar} noValidate>
        <Campo
          id="email"
          rotulo="E-mail"
          type="email"
          autoComplete="username"
          placeholder="nome@veritas.com.br"
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          erro={erros.email}
        />
        <CampoSenha
          id="senha"
          autoComplete="current-password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          erro={erros.senha}
        />
        <p className="login-dica">Esqueceu a senha? Peça ao administrador do sistema para redefinir.</p>
        <button type="submit" className="primario largo" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
      <p className="login-ajuda">
        Ainda não tem conta? <Link to="/cadastro">Criar conta</Link>
      </p>
    </LayoutAcesso>
  );
}
