// Utilitários de DOM.
//
// el() monta elementos com textContent, NUNCA com innerHTML de dados vindos
// da API. Assim uma finalidade como "<img onerror=...>" aparece como texto
// e não vira código executado (proteção contra XSS).

export function el(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (chave.startsWith("on")) elemento.addEventListener(chave.slice(2), valor);
    else if (chave === "class") elemento.className = valor;
    else if (valor === true) elemento.setAttribute(chave, "");
    else elemento.setAttribute(chave, valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === null || filho === undefined || filho === false) continue;
    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return elemento;
}

// Mensagem numa região aria-live: leitores de tela anunciam a mudança.
export function avisar(regiao, texto, tipo = "info") {
  regiao.replaceChildren();
  if (!texto) return;
  regiao.append(el("p", { class: `aviso aviso-${tipo}` }, texto));
}

// Limpa os erros de campo de um formulário.
export function limparErrosDeCampo(form) {
  form.querySelectorAll(".erro-campo").forEach((n) => n.remove());
  form.querySelectorAll("[aria-invalid]").forEach((n) => n.removeAttribute("aria-invalid"));
}

// 422: coloca cada mensagem embaixo do campo com o mesmo "name".
// Devolve as mensagens que não acharam campo (para mostrar no topo).
export function mostrarErrosDeCampo(form, erros = []) {
  limparErrosDeCampo(form);
  const sobras = [];
  for (const { campo, mensagem } of erros) {
    const input = form.elements.namedItem(campo);
    if (!input || !(input instanceof HTMLElement)) {
      sobras.push(`${campo}: ${mensagem}`);
      continue;
    }
    const id = `erro-${form.id || "form"}-${campo}`;
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", id);
    input.insertAdjacentElement("afterend", el("span", { class: "erro-campo", id }, mensagem));
  }
  return sobras;
}
