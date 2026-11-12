"""Exporta o contrato OpenAPI da API.

Uso (na raiz do projeto):
  docker compose exec -T api python -m app.scripts.exportar_openapi > contrato/openapi.json

O contrato é COMMITADO: uma mudança na API aparece como diff neste arquivo
na revisão de código, e o front/Postman podem ser conferidos contra ele.
"""

import json
import sys

from app.main import app


def main() -> None:
    json.dump(app.openapi(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
