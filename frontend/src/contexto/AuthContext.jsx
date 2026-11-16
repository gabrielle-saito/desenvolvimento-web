// Usuário logado compartilhado por todas as telas (Context API).
//
// Qualquer componente pega o usuário com useAuth(), sem passar props de
// tela em tela. O token fica no sessionStorage; o usuário é sempre lido de
// novo da API (/v1/auth/me) ao abrir o site: se o admin mudou o papel de
// alguém, o menu acompanha.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { api, quandoSessaoExpirar } from "../api/cliente.js";
import { apagarToken, obterToken, salvarToken, temPapel } from "../api/sessao.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [usuario, setUsuario] = useState(null);
  // Enquanto confere o token guardado, as rotas protegidas esperam.
  const [carregando, setCarregando] = useState(Boolean(obterToken()));
  const [erroInicial, setErroInicial] = useState(null);

  const sair = useCallback(
    (destino = "/login") => {
      apagarToken();
      setUsuario(null);
      navigate(destino, { replace: true });
    },
    [navigate],
  );

  // 401 em qualquer chamada (token expirou): limpa e volta ao login.
  useEffect(() => {
    quandoSessaoExpirar(() => sair("/login?expirou=1"));
  }, [sair]);

  useEffect(() => {
    if (!obterToken()) return;
    api
      .get("/v1/auth/me")
      .then(setUsuario)
      .catch((erro) => {
        if (erro.status !== 401) setErroInicial(erro);
      })
      .finally(() => setCarregando(false));
  }, []);

  const entrar = useCallback(async (email, senha) => {
    const { access_token: token } = await api.login(email, senha);
    salvarToken(token); // antes do /me: a chamada precisa do token
    try {
      const eu = await api.get("/v1/auth/me");
      setUsuario(eu);
      return eu;
    } catch (erro) {
      apagarToken();
      throw erro;
    }
  }, []);

  const valor = useMemo(
    () => ({
      usuario,
      carregando,
      erroInicial,
      entrar,
      sair,
      tem: (papel) => temPapel(usuario, papel),
    }),
    [usuario, carregando, erroInicial, entrar, sair],
  );
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth() precisa estar dentro de <AuthProvider>.");
  return contexto;
}
