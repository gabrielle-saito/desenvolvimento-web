import * as datas from "../util/datas.js";
import { jaComecou, periodo } from "../util/reservas.js";

// Tabela de reservas com Editar/Cancelar. Usada em "Minhas reservas" e em
// "Gerenciar reservas" (esta mostra também quem reservou).
export default function TabelaReservas({ reservas, mostrarDono = false, aoEditar, aoCancelar }) {
  return (
    <div className="tabela-rolavel">
      <table>
        <thead>
          <tr>
            <th scope="col">Data</th>
            <th scope="col">Horário</th>
            <th scope="col">Sala</th>
            {mostrarDono ? <th scope="col">Reservado por</th> : null}
            <th scope="col">Finalidade</th>
            <th scope="col">
              <span className="visualmente-oculto">Ações</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {reservas.map((r) => (
            <tr key={r.id}>
              <td>{datas.data(r.inicio)}</td>
              <td>{periodo(r)}</td>
              <td>{r.sala.nome}</td>
              {mostrarDono ? <td>{r.usuario.nome}</td> : null}
              <td>{r.finalidade}</td>
              <td className="acoes">
                {jaComecou(r) ? (
                  <span className="discreto">Em andamento</span>
                ) : (
                  <>
                    <button type="button" onClick={() => aoEditar(r)} aria-label={`Editar ${r.finalidade}`}>
                      Editar
                    </button>
                    <button
                      type="button"
                      className="perigo"
                      onClick={() => aoCancelar(r)}
                      aria-label={`Cancelar ${r.finalidade}`}
                    >
                      Cancelar
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
