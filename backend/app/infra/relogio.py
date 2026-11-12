"""O ÚNICO lugar do sistema que lê o relógio.

O domínio recebe o "agora" como parâmetro (ver app/dominio). Centralizar a
leitura aqui deixa claro de onde o tempo vem e facilita trocar o relógio
num teste (monkeypatch de relogio.agora).
"""

from datetime import UTC, datetime


def agora() -> datetime:
    # Sempre com fuso (UTC). datetime.now() sem fuso é ambíguo e
    # não pode ser comparado com as datas do banco (timestamptz).
    return datetime.now(UTC)
