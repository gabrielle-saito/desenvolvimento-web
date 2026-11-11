"""Medição do cenário de desempenho (docs/cenarios-qualidade.md, QA-2).

N usuários simultâneos consultam GET /v1/disponibilidade; mede p50/p95/p99.
Uso (com o ambiente no ar e o seed aplicado):
  docker compose exec api python -m app.scripts.carga_disponibilidade
Variáveis opcionais: CARGA_USUARIOS (30), CARGA_REQUISICOES (20 por usuário),
CARGA_URL (http://localhost:8000).
"""

import os
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx


def main() -> None:
    base = os.environ.get("CARGA_URL", "http://localhost:8000")
    usuarios = int(os.environ.get("CARGA_USUARIOS", "30"))
    por_usuario = int(os.environ.get("CARGA_REQUISICOES", "20"))
    login = httpx.post(
        f"{base}/v1/auth/login",
        data={"username": "ana@empresa.com", "password": os.environ["SEED_SENHA_DEMO"]},
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    inicio = (datetime.now(UTC) + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
    params = {"inicio": inicio.isoformat(), "fim": (inicio + timedelta(hours=1)).isoformat()}

    tempos: list[float] = []
    erros: list[int] = []
    trava = threading.Lock()
    largada = threading.Barrier(usuarios)

    def usuario() -> None:
        with httpx.Client(base_url=base, headers={"Authorization": f"Bearer {token}"}) as cliente:
            largada.wait()  # todos começam juntos
            for _ in range(por_usuario):
                t0 = time.perf_counter()
                r = cliente.get("/v1/disponibilidade", params=params)
                ms = (time.perf_counter() - t0) * 1000
                with trava:
                    tempos.append(ms)
                    if r.status_code != 200:
                        erros.append(r.status_code)

    t0 = time.perf_counter()
    threads = [threading.Thread(target=usuario) for _ in range(usuarios)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duracao = time.perf_counter() - t0

    tempos.sort()

    def pct(q: float) -> float:
        return tempos[min(len(tempos) - 1, int(q * len(tempos)))]

    # Saída para gente (é um relatório de linha de comando, não log da aplicação).
    relatorio = (
        f"usuarios={usuarios} requisicoes={len(tempos)} erros={len(erros)} "
        f"duracao={duracao:.1f}s vazao={len(tempos) / duracao:.0f}req/s\n"
        f"p50={pct(0.50):.0f}ms p95={pct(0.95):.0f}ms p99={pct(0.99):.0f}ms max={tempos[-1]:.0f}ms\n"
        f"meta p95<=500ms: {'OK' if pct(0.95) <= 500 and not erros else 'FALHOU'}\n"
    )
    os.write(1, relatorio.encode())


if __name__ == "__main__":
    main()
