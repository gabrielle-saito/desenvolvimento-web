// Sessão do usuário no navegador.
//
// sessionStorage (e não localStorage): o token some quando a aba é fechada.
// Diminui a janela de uso de um token esquecido num computador compartilhado.

const CHAVE_TOKEN = "reserva-salas:token";
const CHAVE_USUARIO = "reserva-salas:usuario";

export function obterToken() {
  return sessionStorage.getItem(CHAVE_TOKEN);
}

export function salvarSessao(token, usuario) {
  sessionStorage.setItem(CHAVE_TOKEN, token);
  sessionStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
}

export function usuarioDaSessao() {
  const bruto = sessionStorage.getItem(CHAVE_USUARIO);
  return bruto ? JSON.parse(bruto) : null;
}

export function limparSessao() {
  sessionStorage.removeItem(CHAVE_TOKEN);
  sessionStorage.removeItem(CHAVE_USUARIO);
}

// Hierarquia igual à do back-end. ATENÇÃO: isto só decide o que MOSTRAR.
// Quem bloqueia de verdade é a API (403); esconder um botão não é segurança.
const NIVEL = { colaborador: 1, responsavel: 2, admin: 3 };

export function temPapel(usuario, minimo) {
  return Boolean(usuario) && NIVEL[usuario.papel] >= NIVEL[minimo];
}
