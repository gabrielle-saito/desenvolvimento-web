// Rótulo + campo + mensagem de erro, ligados por id (acessibilidade):
// o leitor de tela lê o erro junto com o campo (aria-describedby).
//
// <Campo id="nome" rotulo="Nome" erro={erros.nome} value=... onChange=... />
// <Campo id="papel" rotulo="Papel" como="select">...<option/>...</Campo>
export default function Campo({ id, rotulo, erro, como: Tag = "input", children, className, ...props }) {
  const idErro = `${id}-erro`;
  return (
    <div className={className}>
      <label htmlFor={id}>{rotulo}</label>
      <Tag
        id={id}
        aria-invalid={erro ? "true" : undefined}
        aria-describedby={erro ? idErro : undefined}
        {...props}
      >
        {children}
      </Tag>
      {erro ? (
        <span className="erro-campo" id={idErro}>
          {erro}
        </span>
      ) : null}
    </div>
  );
}
