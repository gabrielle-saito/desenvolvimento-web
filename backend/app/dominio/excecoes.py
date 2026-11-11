"""Exceções de domínio.

O domínio NÃO sabe que HTTP existe: aqui não há status code. Quem traduz
"ConflitoDeHorario" em 409 é a camada de API (app/api/erros.py), com um
handler por família de exceção.
"""


class ErroDeDominio(Exception):
    """Base de todas as regras de negócio violadas."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


# --- Família "não existe" -------------------------------------------------
class NaoEncontrado(ErroDeDominio):
    """A entidade pedida não existe."""


# --- Família "você não pode" ----------------------------------------------
class AcessoNegado(ErroDeDominio):
    """O usuário é conhecido, mas não tem permissão para esta ação."""


# --- Família "dados de entrada fora da regra" ----------------------------
class PeriodoInvalido(ErroDeDominio):
    """Início/fim fora das regras (passado, invertido, curto ou longo demais)."""


# --- Família "o estado atual não permite" (conflito) ----------------------
class Conflito(ErroDeDominio):
    """Base dos conflitos com o estado atual do sistema."""


class ConflitoDeHorario(Conflito):
    """A sala já está ocupada (total ou parcialmente) no período pedido."""

    def __init__(
        self,
        mensagem: str = "Sala ocupada nesse horário. Escolha outro horário ou outra sala.",
        reservas_conflitantes: list[int] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.reservas_conflitantes = reservas_conflitantes or []


class VersaoDesatualizada(Conflito):
    """Locking otimista: alguém alterou a reserva depois que o cliente a leu."""

    def __init__(self, versao_atual: int | None = None) -> None:
        super().__init__(
            "Outra pessoa alterou esta reserva depois que você a abriu. "
            "Recarregue e tente de novo."
        )
        self.versao_atual = versao_atual


class ReservaNaoAlteravel(Conflito):
    """Reserva cancelada ou que já começou."""


class SalaInativa(Conflito):
    """Sala desativada não recebe reservas novas."""


class JaExiste(Conflito):
    """Violação de unicidade: nome de sala ou e-mail repetido."""


class OperacaoProibida(Conflito):
    """Regra de negócio que impede a operação (ex.: admin se desativar)."""
