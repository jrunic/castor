"""Baixar e conferir os irmãos de runtime antes de executar.

A origem é a release da versão em execução: o irmão mora junto do
castor.pyz dessa tag, com a soma publicada ao lado. Soma ausente ou
divergente é recusa — o script baixado ganha sudo e mexe no XDG do usuário.
"""
import hashlib
import subprocess
import tempfile
from pathlib import Path

import castor

ORIGEM_DAS_RELEASES = "https://github.com/jrunic/castor/releases/download"


class ErroDeRuntime(Exception):
    pass


def base_da_versao() -> str:
    """A release cuja tag é a versão em execução — nunca a mais recente.

    Irmão de outra versão chega com a soma certa e o conteúdo errado: a soma
    publicada é a dele.
    """
    return f"{ORIGEM_DAS_RELEASES}/v{castor.__version__}"


def _soma_de(bytes_: bytes) -> str:
    return hashlib.sha256(bytes_).hexdigest()


def baixar_irmao(nome: str, base: str | None = None,
                 executor=subprocess.run) -> Path:
    """instalar-<nome>.sh + .sha256 da base; confere; devolve o caminho."""
    import urllib.request

    base = base or base_da_versao()

    def baixar(caminho: str) -> bytes:
        concluido = executor(
            ["curl", "-fsSL", "--connect-timeout", "15", caminho],
            capture_output=True, text=False)
        if concluido.returncode != 0:
            if caminho.endswith(".sha256"):
                raise ErroDeRuntime(
                    f"não achei a soma publicada em {caminho}. Sem soma, "
                    "nada é executado.")
            raise ErroDeRuntime(f"não baixei {caminho}.")
        return concluido.stdout

    script = baixar(f"{base}/instalar-{nome}.sh")
    soma_bruta = baixar(f"{base}/instalar-{nome}.sh.sha256")
    esperada = soma_bruta.decode("utf-8", "replace").split()[:1]
    if not esperada or esperada[0] != _soma_de(script):
        raise ErroDeRuntime(
            f"o instalador {nome} baixado não bate com a soma publicada. "
            "Nada foi executado.")
    temporario = Path(tempfile.mkdtemp(prefix=f"castor-{nome}-"))
    caminho = temporario / f"instalar-{nome}.sh"
    caminho.write_bytes(script)
    caminho.chmod(0o700)
    return caminho
