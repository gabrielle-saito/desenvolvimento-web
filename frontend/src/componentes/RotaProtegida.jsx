import { Navigate, Outlet, useLocation } from "react-router";

import { mensagemDeErro } from "../api/cliente.js";
import { useAuth } from "../contexto/AuthContext.jsx";
import Carregando from "./Carregando.jsx";

// Protege um grupo de rotas no FRONT-END: sem login vai para /login; sem o
// papel mínimo mostra "Acesso negado". Isto é só conforto de navegação:
// a proteção de verdade é a API, que responde 401/403 de qualquer jeito.
export default function RotaProtegida({ papel = "colaborador" }) {
  const { usuario, carregando, erroInicial, tem } = useAuth();
  const local = useLocation();

  if (carregando) {
    return (
      <main id="conteudo">
        <Carregando />
      </main>
    );
  }
  if (erroInicial) {
    return (
      <main id="conteudo">
        <p className="aviso aviso-erro">{mensagemDeErro(erroInicial)}</p>
      </main>
    );
  }
  if (!usuario) {
    // Guarda para onde a pessoa ia: depois do login ela volta para lá.
    return <Navigate to="/login" replace state={{ voltarPara: local.pathname + local.search }} />;
  }
  if (!tem(papel)) {
    return (
      <>
        <h1>Acesso negado</h1>
        <p className="aviso aviso-erro">Você não tem permissão para acessar esta área.</p>
      </>
    );
  }
  return <Outlet />;
}
