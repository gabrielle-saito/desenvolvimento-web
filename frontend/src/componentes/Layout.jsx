import { Link, NavLink, Outlet } from "react-router";

import logoVeritas from "../assets/logo-veritas.png";
import { useAuth } from "../contexto/AuthContext.jsx";

const NOME_PAPEL = { colaborador: "Colaborador(a)", responsavel: "Responsável", admin: "Administrador(a)" };

// Itens do menu e o papel mínimo para ver cada um. Esconder um item só
// decide o que MOSTRAR: a API também confere o papel (403).
const MENU = [
  { para: "/agenda", texto: "Agenda", papel: "colaborador" },
  { para: "/salas", texto: "Salas", papel: "colaborador" },
  { para: "/reservar", texto: "Reservar sala", papel: "colaborador" },
  { para: "/minhas", texto: "Minhas reservas", papel: "colaborador" },
  { para: "/gerenciar", texto: "Gerenciar reservas", papel: "responsavel" },
  { para: "/admin", texto: "Administração", papel: "admin" },
];

// "Mariana Souza" -> "MS"; "Ana" -> "A".
function iniciais(nome) {
  const partes = String(nome).trim().split(/\s+/).filter(Boolean);
  const letras = partes.length > 1 ? [partes[0], partes[partes.length - 1]] : partes;
  return letras.map((p) => p[0].toUpperCase()).join("");
}

// Estrutura das telas de quem está logado: barra superior + conteúdo.
export default function Layout() {
  const { usuario, sair, tem } = useAuth();
  return (
    <>
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="topo">
        <Link className="marca" to="/agenda">
          <img src={logoVeritas} alt="Veritas" width="132" height="32" />
        </Link>
        <nav id="menu" aria-label="Menu principal">
          <ul>
            {MENU.filter((item) => tem(item.papel)).map((item) => (
              <li key={item.para}>
                {/* NavLink coloca aria-current="page" no item da tela atual. */}
                <NavLink to={item.para}>{item.texto}</NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="usuario-logado">
          <span className="avatar" aria-hidden="true">
            {iniciais(usuario.nome)}
          </span>
          <span className="usuario-texto">
            <strong>{usuario.nome}</strong>
            <span className="usuario-papel">{NOME_PAPEL[usuario.papel] ?? usuario.papel}</span>
          </span>
          <button type="button" className="botao-fantasma" onClick={() => sair()}>
            Sair
          </button>
        </div>
      </header>
      <main id="conteudo" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  );
}
