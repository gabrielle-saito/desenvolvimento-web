"""NÚCLEO PURO do sistema: enums, regras e exceções de domínio.

Regra de arquitetura (verificada por tests/test_arquitetura.py):
nada aqui importa fastapi, sqlalchemy, pydantic, app.api, app.db, app.models,
app.repositorios nem chama datetime.now. O "agora" entra como parâmetro.
Assim as regras são testáveis sem banco, sem HTTP e sem relógio.
"""
