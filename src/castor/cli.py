import argparse

AREAS = ("segredos", "servico", "rotina", "ronda", "atualizacao")


def construir_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="castor",
        description="Toolkit de infra pessoal: segredos, serviço, rotina, ronda e atualização.",
    )
    areas = analisador.add_subparsers(dest="area", metavar="area", required=True)
    for nome in AREAS:
        areas.add_parser(nome, help=f"área {nome}")
    return analisador


def principal(argumentos: list[str] | None = None) -> int:
    construir_analisador().parse_args(argumentos)
    return 0


def executar() -> None:
    raise SystemExit(principal())
