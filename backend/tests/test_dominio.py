"""Testes das regras de domínio: sem banco, sem HTTP, sem relógio.

O "agora" é uma data FIXA. Por isso estes testes rodam em milissegundos e dão
o mesmo resultado a qualquer hora do dia.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.dominio.enums import Papel, StatusReserva
from app.dominio.excecoes import (
    AcessoNegado,
    OperacaoProibida,
    PeriodoInvalido,
    ReservaNaoAlteravel,
    SalaInativa,
    VersaoDesatualizada,
)
from app.dominio.permissoes import (
    exigir_pode_alterar_reserva,
    pode_alterar_reserva,
    tem_papel_minimo,
    validar_alteracao_do_proprio_admin,
)
from app.dominio.reservas import (
    DURACAO_MAXIMA,
    DURACAO_MINIMA,
    garantir_reserva_alteravel,
    garantir_sala_ativa,
    ha_sobreposicao,
    validar_periodo,
    validar_periodo_de_consulta,
    verificar_versao,
)

AGORA = datetime(2030, 3, 10, 9, 0, tzinfo=UTC)


def h(hora: int, minuto: int = 0) -> datetime:
    """Atalho: um horário no dia 10/03/2030 (UTC)."""
    return datetime(2030, 3, 10, hora, minuto, tzinfo=UTC)


@dataclass
class ReservaFake:
    """Objeto simples no lugar do modelo ORM (o domínio só precisa destes campos)."""

    usuario_id: int
    inicio: datetime
    status: StatusReserva = StatusReserva.ATIVA


# ---------------------------------------------------------------- sobreposição
@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        ((h(10), h(11)), (h(10), h(11)), True),  # idênticas
        ((h(10), h(11)), (h(10, 30), h(11, 30)), True),  # parcial no fim
        ((h(10), h(11)), (h(9, 30), h(10, 30)), True),  # parcial no início
        ((h(10), h(12)), (h(10, 30), h(11)), True),  # B dentro de A
        ((h(10, 30), h(11)), (h(10), h(12)), True),  # A dentro de B
        ((h(10), h(11)), (h(11), h(12)), False),  # encostadas: A termina quando B começa
        ((h(11), h(12)), (h(10), h(11)), False),  # encostadas, ordem inversa
        ((h(10), h(11)), (h(13), h(14)), False),  # distantes
    ],
)
def test_ha_sobreposicao_semantica_semiaberta(a, b, esperado) -> None:
    assert ha_sobreposicao(*a, *b) is esperado
    # Sobreposição é simétrica.
    assert ha_sobreposicao(*b, *a) is esperado


# -------------------------------------------------------------------- período
def test_periodo_valido_passa() -> None:
    validar_periodo(h(10), h(11), AGORA)


def test_periodo_comecando_agora_passa() -> None:
    validar_periodo(AGORA, AGORA + timedelta(hours=1), AGORA)


@pytest.mark.parametrize(
    ("inicio", "fim", "trecho"),
    [
        (h(11), h(10), "depois do início"),  # invertido
        (h(10), h(10), "depois do início"),  # duração zero
        (h(8), h(9, 30), "já passou"),  # começa no passado
        (h(10), h(10, 14), "mínimo"),  # 14 min
        (h(10), h(18, 1), "máximo"),  # 8h01
    ],
)
def test_periodo_invalido(inicio, fim, trecho) -> None:
    with pytest.raises(PeriodoInvalido, match=trecho):
        validar_periodo(inicio, fim, AGORA)


def test_duracoes_limite_exatas_sao_aceitas() -> None:
    validar_periodo(h(10), h(10) + DURACAO_MINIMA, AGORA)
    validar_periodo(h(10), h(10) + DURACAO_MAXIMA, AGORA)


def test_periodo_sem_fuso_e_invalido() -> None:
    sem_fuso = datetime(2030, 3, 10, 10, 0)
    with pytest.raises(PeriodoInvalido, match="fuso"):
        validar_periodo(sem_fuso, sem_fuso + timedelta(hours=1), AGORA)


def test_periodo_compara_instantes_e_nao_relogio_de_parede() -> None:
    # 07:30 em São Paulo (UTC-3) = 10:30 UTC, que está no futuro em relação a AGORA (09:00 UTC).
    sp = timezone(timedelta(hours=-3))
    inicio = datetime(2030, 3, 10, 7, 30, tzinfo=sp)
    validar_periodo(inicio, inicio + timedelta(hours=1), AGORA)


# ----------------------------------------------------- reserva alterável / sala
def test_reserva_ativa_futura_e_alteravel() -> None:
    garantir_reserva_alteravel(ReservaFake(usuario_id=1, inicio=h(10)), AGORA)


def test_reserva_cancelada_nao_e_alteravel() -> None:
    reserva = ReservaFake(usuario_id=1, inicio=h(10), status=StatusReserva.CANCELADA)
    with pytest.raises(ReservaNaoAlteravel, match="cancelada"):
        garantir_reserva_alteravel(reserva, AGORA)


@pytest.mark.parametrize("inicio", [AGORA, AGORA - timedelta(minutes=1)])
def test_reserva_que_ja_comecou_nao_e_alteravel(inicio) -> None:
    with pytest.raises(ReservaNaoAlteravel, match="começou"):
        garantir_reserva_alteravel(ReservaFake(usuario_id=1, inicio=inicio), AGORA)


def test_sala_inativa_nao_recebe_reserva() -> None:
    garantir_sala_ativa(True)
    with pytest.raises(SalaInativa):
        garantir_sala_ativa(False)


# --------------------------------------------------------------------- versão
def test_versao_igual_passa_e_diferente_falha_com_versao_atual() -> None:
    verificar_versao(3, 3)
    with pytest.raises(VersaoDesatualizada) as exc:
        verificar_versao(2, 3)
    assert exc.value.versao_atual == 3


# ---------------------------------------------------------------- permissões
def test_hierarquia_de_papeis() -> None:
    assert tem_papel_minimo(Papel.ADMIN, Papel.RESPONSAVEL)
    assert tem_papel_minimo(Papel.RESPONSAVEL, Papel.RESPONSAVEL)
    assert not tem_papel_minimo(Papel.COLABORADOR, Papel.RESPONSAVEL)
    assert not tem_papel_minimo(Papel.RESPONSAVEL, Papel.ADMIN)


@pytest.mark.parametrize(
    ("papel", "usuario_id", "pode"),
    [
        (Papel.COLABORADOR, 1, True),  # dono
        (Papel.COLABORADOR, 2, False),  # colaborador, reserva alheia
        (Papel.RESPONSAVEL, 2, True),
        (Papel.ADMIN, 2, True),
    ],
)
def test_pode_alterar_reserva(papel, usuario_id, pode) -> None:
    reserva = ReservaFake(usuario_id=1, inicio=h(10))
    assert pode_alterar_reserva(papel, usuario_id, reserva) is pode


def test_colaborador_em_reserva_alheia_recebe_acesso_negado() -> None:
    with pytest.raises(AcessoNegado):
        exigir_pode_alterar_reserva(Papel.COLABORADOR, 2, ReservaFake(usuario_id=1, inicio=h(10)))


def test_admin_nao_pode_se_desativar_nem_se_rebaixar() -> None:
    with pytest.raises(OperacaoProibida, match="desativar"):
        validar_alteracao_do_proprio_admin(1, 1, novo_papel=None, novo_ativo=False)
    with pytest.raises(OperacaoProibida, match="papel"):
        validar_alteracao_do_proprio_admin(1, 1, novo_papel=Papel.RESPONSAVEL, novo_ativo=None)


def test_admin_pode_alterar_outro_usuario_e_a_si_mesmo_sem_se_rebaixar() -> None:
    validar_alteracao_do_proprio_admin(1, 2, novo_papel=Papel.COLABORADOR, novo_ativo=False)
    validar_alteracao_do_proprio_admin(1, 1, novo_papel=Papel.ADMIN, novo_ativo=True)


# ------------------------------------------------------- período de consulta
def test_periodo_de_consulta_aceita_passado_mas_nao_invertido_nem_longo() -> None:
    validar_periodo_de_consulta(h(8) - timedelta(days=3), h(8))  # passado: ok
    with pytest.raises(PeriodoInvalido, match="depois do início"):
        validar_periodo_de_consulta(h(11), h(10))
    with pytest.raises(PeriodoInvalido, match="31 dias"):
        validar_periodo_de_consulta(h(10), h(10) + timedelta(days=32))
