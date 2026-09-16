"""Baixar e conferir os irmãos de runtime antes de executar.

A origem é sempre a release do castor: o irmão mora na mesma pasta do
castor.pyz, com a soma publicada ao lado. Soma ausente ou divergente é
recusa — o script baixado ganha sudo e mexe no XDG do usuário.
"""
import hashlib
import subprocess
import tempfile
from pathlib import Path

BASE_DA_RELEASE = "https://github.com/jrunic/castor/releases/latest/download"


class ErroDeRuntime(Exception):
    pass


def _soma_de(bytes_: bytes) -> str:
    return hashlib.sha256(bytes_).hexdigest()


def baixar_irmao(nome: str, base: str = BASE_DA_RELEASE,
                 executor=subprocess.run) -> Path:
    """instalar-<nome>.sh + .sha256 da base; confere; devolve o caminho."""
    import urllib.request

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
