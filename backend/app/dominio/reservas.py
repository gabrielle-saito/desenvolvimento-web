"""Regras de reserva: funções puras.

"Pura" = o resultado depende só dos parâmetros. Nada de banco, HTTP ou
relógio: o "agora" chega como parâmetro. Isso torna as regras testáveis com
datas fixas (o teste das 23h59 não quebra à meia-noite).
"""

from datetime import datetime, timedelta
from typing import Protocol

from app.dominio.enums import StatusReserva
from app.dominio.excecoes import (
    PeriodoInvalido,
    ReservaNaoAlteravel,
    SalaInativa,
    VersaoDesatualizada,
)

# Limites do negócio, num lugar só.
DURACAO_MINIMA = timedelta(minutes=15)
DURACAO_MAXIMA = timedelta(hours=8)


class ReservaLike(Protocol):
    """O que as regras precisam saber de uma reserva. Protocol (duck typing):
    o domínio não importa o modelo ORM, mas aceita qualquer objeto com estes
    atributos — o modelo Reserva, um DTO ou um objeto de teste."""

    usuario_id: int
    inicio: datetime
    status: StatusReserva


def _exigir_fuso(nome: str, valor: datetime) -> None:
    # Data sem fuso é ambígua ("10h" de onde?). A API já recusa com 422 no
    # Pydantic; o domínio se protege mesmo assim (defesa em profundidade).
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise PeriodoInvalido(f"'{nome}' precisa informar o fuso horário.")


def validar_periodo(inicio: datetime, fim: datetime, agora: datetime) -> None:
    """Levanta PeriodoInvalido se o período não puder ser reservado."""
    _exigir_fuso("inicio", inicio)
    _exigir_fuso("fim", fim)
    if fim <= inicio:
        raise PeriodoInvalido("O fim da reserva precisa ser depois do início.")
    if inicio < agora:
        raise PeriodoInvalido("Não é possível reservar um horário que já passou.")
    duracao = fim - inicio
    if duracao < DURACAO_MINIMA:
        minutos = int(DURACAO_MINIMA.total_seconds() // 60)
        raise PeriodoInvalido(f"A reserva precisa ter no mínimo {minutos} minutos.")
    if duracao > DURACAO_MAXIMA:
        horas = int(DURACAO_MAXIMA.total_seconds() // 3600)
        raise PeriodoInvalido(f"A reserva pode ter no máximo {horas} horas.")


def ha_sobreposicao(
    a_inicio: datetime, a_fim: datetime, b_inicio: datetime, b_fim: datetime
) -> bool:
    """Semântica [inicio, fim): inclui o início e exclui o fim — a mesma da
    constraint tstzrange(inicio, fim, '[)') no banco. Logo 10h-11h e 11h-12h
    NÃO se sobrepõem (reservas encostadas são permitidas)."""
    return a_inicio < b_fim and b_inicio < a_fim


def garantir_reserva_alteravel(reserva: ReservaLike, agora: datetime) -> None:
    """Reserva cancelada ou já iniciada não pode ser editada nem cancelada."""
    if reserva.status == StatusReserva.CANCELADA:
        raise ReservaNaoAlteravel("Esta reserva já foi cancelada.")
    if reserva.inicio <= agora:
        raise ReservaNaoAlteravel(
            "Esta reserva já começou e não pode mais ser alterada nem cancelada."
        )


def garantir_sala_ativa(sala_ativa: bool) -> None:
    if not sala_ativa:
        raise SalaInativa("Esta sala está desativada e não recebe novas reservas.")


def verificar_versao(versao_enviada: int, versao_atual: int) -> None:
    """Locking otimista: o cliente prova que alterou a versão que leu."""
    if versao_enviada != versao_atual:
        raise VersaoDesatualizada(versao_atual=versao_atual)
