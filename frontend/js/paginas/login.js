import { api, ErroApi, mensagemDeErro } from "../api.js";
import { avisar, limparErrosDeCampo, mostrarErrosDeCampo } from "../dom.js";
import { salvarSessao } from "../sessao.js";

const form = document.getElementById("form-login");
const avisos = document.getElementById("avisos");

if (new URLSearchParams(window.location.search).has("expirou")) {
  avisar(avisos, "Sua sessão expirou. Entre novamente.", "info");
}

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  limparErrosDeCampo(form);
  const email = form.email.value.trim();
  const senha = form.senha.value;
  const faltando = [];
  if (!email) faltando.push({ campo: "email", mensagem: "Informe o e-mail." });
  if (!senha) faltando.push({ campo: "senha", mensagem: "Informe a senha." });
  if (faltando.length) {
    mostrarErrosDeCampo(form, faltando);
    return;
  }

  const botao = form.querySelector("button");
  botao.disabled = true;
  try {
    const { access_token: token } = await api.login(email, senha);
    // Guarda o token antes de chamar /me (a chamada precisa dele).
    salvarSessao(token, null);
    const usuario = await api.get("/v1/auth/me");
    salvarSessao(token, usuario);
    window.location.href = "agenda.html";
  } catch (erro) {
    const texto =
      erro instanceof ErroApi && erro.status === 401
        ? "E-mail ou senha inválidos."
        : mensagemDeErro(erro);
    avisar(avisos, texto, "erro");
  } finally {
    botao.disabled = false;
  }
});
