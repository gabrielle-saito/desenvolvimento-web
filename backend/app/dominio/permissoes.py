"""Regras de permissão (RBAC). Funções puras: recebem o papel e os ids,
respondem sim/não ou levantam a exceção de domínio."""

from app.dominio.enums import Papel
from app.dominio.excecoes import AcessoNegado, OperacaoProibida
from app.dominio.reservas import ReservaLike

# Hierarquia: cada papel tem tudo do anterior.
_NIVEL = {Papel.COLABORADOR: 1, Papel.RESPONSAVEL: 2, Papel.ADMIN: 3}


def tem_papel_minimo(papel: Papel, minimo: Papel) -> bool:
    return _NIVEL[Papel(papel)] >= _NIVEL[Papel(minimo)]


def pode_alterar_reserva(papel: Papel, usuario_id: int, reserva: ReservaLike) -> bool:
    """Dono da reserva, responsável pelas salas ou admin."""
    return reserva.usuario_id == usuario_id or tem_papel_minimo(papel, Papel.RESPONSAVEL)


def exigir_pode_alterar_reserva(papel: Papel, usuario_id: int, reserva: ReservaLike) -> None:
    if not pode_alterar_reserva(papel, usuario_id, reserva):
        raise AcessoNegado("Você só pode alterar ou cancelar as suas próprias reservas.")


def validar_alteracao_do_proprio_admin(
    ator_id: int,
    alvo_id: int,
    novo_papel: Papel | None,
    novo_ativo: bool | None,
) -> None:
    """Um admin não pode se desativar nem tirar o próprio papel de admin.
    Evita o sistema ficar sem nenhum admin por um clique errado."""
    if ator_id != alvo_id:
        return
    if novo_ativo is False:
        raise OperacaoProibida("Você não pode desativar a sua própria conta.")
    if novo_papel is not None and Papel(novo_papel) != Papel.ADMIN:
        raise OperacaoProibida("Você não pode remover o seu próprio papel de admin.")
