"""Trabalho de startup que vale por container, não por processo.

Com `--workers N` o `on_startup` do FastAPI roda uma vez por worker, e um worker
que respawne no meio do dia invalidaria o cache de todos e apagaria o `.tmp` que
outro está escrevendo. Estas duas rotinas rodam aqui, antes do uvicorn subir.
"""

from services.cache import invalidar_artefatos_em_disco, limpar_tmp_orfaos


def main() -> None:
    removidos = limpar_tmp_orfaos()
    if removidos:
        print(f"[startup] .tmp/.inflight órfãos removidos: {len(removidos)}")
    invalidar_artefatos_em_disco()
    print("[startup] artefatos em disco invalidados")


if __name__ == "__main__":
    main()
