// Token no navegador.
//
// sessionStorage (e não localStorage): o token some quando a aba é fechada.
// Diminui a janela de uso de um token esquecido num computador compartilhado.

const CHAVE_TOKEN = "reserva-salas:token";

export function obterToken() {
  try {
    return sessionStorage.getItem(CHAVE_TOKEN);
  } catch {
    return null;
  }
}

export function salvarToken(token) {
  try {
    sessionStorage.setItem(CHAVE_TOKEN, token);
  } catch {
    // Navegador sem storage (modo restrito): a sessão vale só até recarregar.
  }
}

export function apagarToken() {
  try {
    sessionStorage.removeItem(CHAVE_TOKEN);
  } catch {
    // idem
  }
}

// Hierarquia igual à do back-end. ATENÇÃO: isto só decide o que MOSTRAR.
// Quem bloqueia de verdade é a API (403); esconder um botão não é segurança.
const NIVEL = { colaborador: 1, responsavel: 2, admin: 3 };

export function temPapel(usuario, minimo) {
  return Boolean(usuario) && NIVEL[usuario.papel] >= NIVEL[minimo];
}
