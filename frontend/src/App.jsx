import { Navigate, Route, Routes } from "react-router";

import Layout from "./componentes/Layout.jsx";
import RotaProtegida from "./componentes/RotaProtegida.jsx";
import AdminLayout from "./paginas/admin/AdminLayout.jsx";
import AdminRecursos from "./paginas/admin/AdminRecursos.jsx";
import AdminSalas from "./paginas/admin/AdminSalas.jsx";
import AdminUsuarios from "./paginas/admin/AdminUsuarios.jsx";
import Agenda from "./paginas/Agenda.jsx";
import Cadastro from "./paginas/Cadastro.jsx";
import Catalogo from "./paginas/Catalogo.jsx";
import GerenciarReservas from "./paginas/GerenciarReservas.jsx";
import Login from "./paginas/Login.jsx";
import MinhasReservas from "./paginas/MinhasReservas.jsx";
import NaoEncontrada from "./paginas/NaoEncontrada.jsx";
import Reservar from "./paginas/Reservar.jsx";

// Rotas no cliente (React Router). Cada nível de RotaProtegida exige um
// papel mínimo; o Layout (barra + menu) envolve as telas de quem entrou.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />

      <Route element={<RotaProtegida />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/agenda" replace />} />
          <Route path="agenda" element={<Agenda />} />
          <Route path="salas" element={<Catalogo />} />
          <Route path="reservar" element={<Reservar />} />
          <Route path="minhas" element={<MinhasReservas />} />

          <Route element={<RotaProtegida papel="responsavel" />}>
            <Route path="gerenciar" element={<GerenciarReservas />} />
          </Route>

          <Route element={<RotaProtegida papel="admin" />}>
            <Route path="admin" element={<AdminLayout />}>
              <Route index element={<Navigate to="salas" replace />} />
              <Route path="salas" element={<AdminSalas />} />
              <Route path="recursos" element={<AdminRecursos />} />
              <Route path="usuarios" element={<AdminUsuarios />} />
            </Route>
          </Route>

          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Route>
    </Routes>
  );
}
