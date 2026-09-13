"""O que a máquina responde sobre si mesma.

Nada aqui é perguntado ao usuário: diretório, usuário, sistema e versão vêm da
própria máquina. Cada campo digitado é um caminho errado que ninguém vai saber
diagnosticar depois.
"""
from dataclasses import dataclass

CAMPOS = ("usuario", "casa", "sistema", "epoca", "fuso", "python", "sudo")

# Uma linha, sem aspas simples: o texto atravessa o shell local, o ssh e o
# shell remoto. A versão do python vem de 'python3 -V' para não aninhar aspas.
SONDA = "; ".join((
    'printf "usuario=%s\\n" "$(id -un)"',
    'printf "casa=%s\\n" "$HOME"',
    'printf "sistema=%s\\n" "$(uname -s)"',
    'printf "epoca=%s\\n" "$(date +%s)"',
    'printf "fuso=%s\\n" "$(date +%z)"',
    'printf "python=%s\\n" "$(python3 -V 2>&1 || echo ausente)"',
    'printf "sudo=%s\\n" "$(sudo -n true 2>/dev/null && echo sim || echo nao)"',
))

VERSAO_MINIMA = (3, 12)
TOLERANCIA_DO_RELOGIO = 120


class MedicaoIncompleta(Exception):
    pass


@dataclass(frozen=True)
class Medicao:
    usuario: str
    casa: str
    sistema: str
    epoca: int
    fuso: str
    python: str
    sudo: bool


def interpretar(texto: str) -> Medicao:
    campos = {}
    for linha in texto.splitlines():
        if "=" in linha:
            nome, valor = linha.split("=", 1)
            if nome.strip() in CAMPOS:
                campos[nome.strip()] = valor.strip()
    faltando = [campo for campo in CAMPOS if campo not in campos]
    if faltando:
        raise MedicaoIncompleta(
            f"a máquina não respondeu {', '.join(faltando)}. A sonda chegou "
            f"truncada ou o shell remoto não é compatível com sh."
        )
    bruto = campos["python"]
    versao = bruto.split()[-1] if bruto.lower().startswith("python") else ""
    return Medicao(
        usuario=campos["usuario"],
        casa=campos["casa"],
        sistema=campos["sistema"].lower(),
        epoca=int(campos["epoca"]),
        fuso=campos["fuso"],
        python=versao,
        sudo=campos["sudo"] == "sim",
    )


def conferir_relogio(medido: Medicao, agora: float,
                     tolerancia: int = TOLERANCIA_DO_RELOGIO) -> str | None:
    desvio = int(abs(medido.epoca - agora))
    if desvio <= tolerancia:
        return None
    return (f"o relógio da máquina está {desvio} segundos fora do desta. "
            f"Registro com hora errada e certificado vencido nascem daqui. "
            f"Ligue a sincronização de hora (timedatectl set-ntp true) e repita.")


def conferir_python(medido: Medicao,
                    minimo: tuple[int, int] = VERSAO_MINIMA) -> str | None:
    if not medido.python:
        return ("não achei python3 na máquina. O castor precisa de "
                f"{minimo[0]}.{minimo[1]} ou mais novo.")
    partes = tuple(int(p) for p in medido.python.split(".")[:2] if p.isdigit())
    if partes < minimo:
        return (f"o python da máquina é {medido.python}; o castor precisa de "
                f"{minimo[0]}.{minimo[1]} ou mais novo.")
    return None
