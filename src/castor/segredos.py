from pathlib import Path

from castor.expansao import expandir
from castor.manifesto import ErroDeManifesto, Maquina


class ModeloInvalido(ErroDeManifesto):
    pass


def gerar(modelo: Path, maquina: Maquina, destino: Path) -> Path:
    """Resolve o modelo para a máquina e grava o arquivo de serviço.

    Grava em arquivo, nunca na saída padrão: o conteúdo é segredo.
    """
    resolvido = []
    for numero, linha in enumerate(Path(modelo).read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if "=" not in linha:
            raise ModeloInvalido(f"{modelo}:{numero}: linha sem atribuição: {linha!r}")
        linha_resolvida = expandir(linha, maquina)
        chave, valor = linha_resolvida.split("=", 1)
        # O arquivo é lido por dois consumidores com regras diferentes de
        # expansão. Valor que os faria divergir é recusado na origem.
        if "$" in valor or "`" in valor:
            raise ModeloInvalido(
                f"{modelo}:{numero}: valor de {chave} tem cifrão ou crase, que o shell "
                f"expande e o systemd lê literal. Os dois consumidores divergiriam."
            )
        resolvido.append(linha_resolvida)

    destino = Path(destino)
    destino.write_text("\n".join(resolvido) + "\n", encoding="utf-8")
    destino.chmod(0o600)
    return destino
