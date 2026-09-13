import argparse
import os
import sys
from pathlib import Path

from castor import manifesto as mod_manifesto
from castor import segredos as mod_segredos
from castor.manifesto import ErroDeManifesto

AREAS = ("segredos", "servico", "rotina", "ronda", "atualizacao")


def construir_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="castor",
        description="Toolkit de infra pessoal: segredos, serviço, rotina, ronda e atualização.",
    )
    analisador.add_argument(
        "--manifesto",
        default=os.environ.get("CASTOR_MANIFESTO", "castor.json"),
        help="caminho do manifesto (default: $CASTOR_MANIFESTO ou ./castor.json)",
    )
    areas = analisador.add_subparsers(dest="area", metavar="area", required=True)

    segredos = areas.add_parser("segredos", help="área segredos")
    verbos = segredos.add_subparsers(dest="verbo", metavar="verbo", required=True)

    gerar = verbos.add_parser("gerar", help="resolve o modelo e grava o arquivo de serviço")
    gerar.add_argument("modelo")
    gerar.add_argument("--maquina", required=True)
    gerar.add_argument("--destino", required=True)

    ver = verbos.add_parser("ver", help="descreve a variável sem imprimir o valor")
    ver.add_argument("arquivo")
    ver.add_argument("variavel")
    ver.add_argument("--revelar", action="store_true",
                     help="imprime o VALOR do segredo na saída padrão")

    for nome in AREAS:
        if nome != "segredos":
            areas.add_parser(nome, help=f"área {nome}")
    return analisador


def _despachar_segredos(opcoes) -> int:
    if opcoes.verbo == "gerar":
        maquina = mod_manifesto.ler(Path(opcoes.manifesto)).maquina(opcoes.maquina)
        destino = mod_segredos.gerar(Path(opcoes.modelo), maquina, Path(opcoes.destino))
        print(f"gravado: {destino}")
        return 0
    print(mod_segredos.ver(Path(opcoes.arquivo), opcoes.variavel, revelar=opcoes.revelar))
    return 0


def principal(argumentos: list[str] | None = None) -> int:
    opcoes = construir_analisador().parse_args(argumentos)
    try:
        if opcoes.area == "segredos":
            return _despachar_segredos(opcoes)
    except ErroDeManifesto as erro:
        print(str(erro), file=sys.stderr)
        return 1
    print(f"área '{opcoes.area}' ainda não tem verbos nesta versão.", file=sys.stderr)
    return 1


def executar() -> None:
    raise SystemExit(principal())
