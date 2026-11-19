import logoVeritas from "../assets/logo-veritas-branca.png";

// Duas colunas das telas de entrada (login e cadastro): destaque vinho à
// esquerda, formulário à direita. No celular as colunas empilham.
export default function LayoutAcesso({ children }) {
  return (
    <div className="pagina-login">
      <aside className="login-destaque">
        <p className="login-marca">
          <img src={logoVeritas} alt="Veritas" width="132" height="30" />
          <span>Reserva de salas</span>
        </p>
        <div className="login-chamada">
          <h2>Encontre uma sala livre e reserve em segundos.</h2>
          <p>Veja a agenda de todas as salas da Veritas e garanta o seu horário sem conflito com ninguém.</p>
        </div>
      </aside>
      <main id="conteudo" className="login-painel">
        <div className="login-form">{children}</div>
      </main>
    </div>
  );
}
