"""A chave de acesso da máquina principal às clientes.

A privada vive no lugar padrão do sistema (~/.ssh), e não no cofre: quem já usa
ssh e git continua usando. O manifesto guarda apenas o caminho.
"""
import subprocess
from pathlib import Path


class ErroDeChave(Exception):
    """Base dos erros desta área."""


class ChaveJaExiste(ErroDeChave):
    pass


class ChaveAusente(ErroDeChave):
    pass


class ChavePublicaAusente(ErroDeChave):
    pass


class ChaveInvalida(ErroDeChave):
    pass


CAMINHO_PADRAO = Path("~/.ssh/castor")


def caminho_padrao() -> Path:
    return CAMINHO_PADRAO.expanduser()


def publica_de(privada: Path) -> Path:
    return Path(str(privada) + ".pub")


def criar(caminho: Path, *, comentario: str = "castor",
          executor=subprocess.run) -> Path:
    """Cria o par. Nunca sobrescreve: chave sobrescrita é acesso perdido."""
    privada = Path(caminho).expanduser()
    if privada.exists():
        raise ChaveJaExiste(
            f"já existe uma chave em {privada}. Para usá-la, rode "
            f"'castor chave usar {privada}'. Nada foi sobrescrito."
        )
    privada.parent.mkdir(parents=True, exist_ok=True)
    privada.parent.chmod(0o700)
    executor(
        ["ssh-keygen", "-t", "ed25519", "-f", str(privada), "-N", "",
         "-C", comentario],
        capture_output=True, text=True, check=True,
    )
    privada.chmod(0o600)
    return privada


def adotar(caminho: Path, *, executor=subprocess.run) -> Path:
    """Adota uma chave que o usuário já tem."""
    privada = Path(caminho).expanduser()
    if not privada.exists():
        raise ChaveAusente(f"não achei chave em {privada}.")
    publica = publica_de(privada)
    if not publica.exists():
        raise ChavePublicaAusente(
            f"achei {privada} mas não {publica}. A pública é o que "
            f"vai para a máquina cliente; sem ela não dá para instalar o acesso."
        )
    prova = executor(
        ["ssh-keygen", "-y", "-f", str(privada)],
        capture_output=True, text=True,
    )
    if prova.returncode != 0:
        raise ChaveInvalida(
            f"{privada} não é uma chave privada que o ssh-keygen consiga ler."
        )
    derivada = prova.stdout.split()[:2]
    declarada = publica.read_text(encoding="utf-8").split()[:2]
    if derivada != declarada:
        raise ChaveInvalida(
            f"a pública em {publica} não corresponde a {privada}."
        )
    return privada


def mostrar(caminho: Path) -> str:
    privada = Path(caminho).expanduser()
    publica = publica_de(privada)
    if not publica.exists():
        raise ChavePublicaAusente(f"não achei {publica}.")
    return publica.read_text(encoding="utf-8").strip()
