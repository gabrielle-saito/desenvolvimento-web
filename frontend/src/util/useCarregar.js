import { useCallback, useEffect, useState } from "react";

// Busca dados da API e guarda os três estados que toda tela precisa tratar:
// carregando, erro e os dados. Refaz a busca quando "deps" muda ou quando
// recarregar() é chamado. Durante uma recarga os dados antigos continuam
// na tela (sem piscar "Carregando…" a cada atualização).
export function useCarregar(buscar, deps) {
  const [estado, setEstado] = useState({ dados: null, carregando: true, erro: null });
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let ativo = true; // ignora respostas que chegam depois de sair da tela
    setEstado((e) => ({ ...e, carregando: true, erro: null }));
    buscar()
      .then((dados) => ativo && setEstado({ dados, carregando: false, erro: null }))
      .catch((erro) => ativo && setEstado((e) => ({ ...e, carregando: false, erro })));
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  return { ...estado, recarregar };
}

// Título da aba do navegador.
export function useTitulo(titulo) {
  useEffect(() => {
    document.title = titulo ? `${titulo} · Veritas Reserva de Salas` : "Veritas Reserva de Salas";
  }, [titulo]);
}
