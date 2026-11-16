import { NavLink, Outlet } from "react-router";

import { useTitulo } from "../../util/useCarregar.js";

// Área do admin: abas Salas, Recursos e Usuários (cada uma é uma rota).
export default function AdminLayout() {
  useTitulo("Administração");
  return (
    <>
      <h1>Administração</h1>
      <nav className="abas" aria-label="Seções da administração">
        <NavLink to="/admin/salas">Salas</NavLink>
        <NavLink to="/admin/recursos">Recursos</NavLink>
        <NavLink to="/admin/usuarios">Usuários</NavLink>
      </nav>
      <Outlet />
    </>
  );
}
