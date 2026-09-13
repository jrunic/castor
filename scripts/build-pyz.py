import argparse
import zipapp
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def interessa(caminho: Path) -> bool:
    """Deixa de fora cache e resíduo de execução."""
    return "__pycache__" not in caminho.parts and caminho.suffix != ".pyc"


def principal() -> int:
    analisador = argparse.ArgumentParser(description="Monta castor.pyz a partir de src/.")
    analisador.add_argument("--saida", default=str(RAIZ / "dist" / "castor.pyz"))
    opcoes = analisador.parse_args()

    saida = Path(opcoes.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    # `executar` levanta SystemExit com o código de `principal`. Apontar para
    # `principal` faria o pacote descartar o retorno e sair 0 em toda falha.
    zipapp.create_archive(
        source=RAIZ / "src",
        target=saida,
        interpreter="/usr/bin/env python3",
        main="castor.cli:executar",
        filter=interessa,
    )
    print(f"gerado: {saida}")
    return 0


raise SystemExit(principal())
