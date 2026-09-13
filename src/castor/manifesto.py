import json
from dataclasses import dataclass
from pathlib import Path


class ErroDeManifesto(Exception):
    """Base dos erros desta área."""


class MaquinaDesconhecida(ErroDeManifesto):
    pass


@dataclass(frozen=True)
class Maquina:
    nome: str
    usuario: str
    casa: str
    sistema: str


@dataclass(frozen=True)
class Manifesto:
    origem: Path
    dados: dict

    def maquina(self, nome: str) -> Maquina:
        declarada = self.dados.get("maquinas", {}).get(nome)
        if declarada is None:
            raise MaquinaDesconhecida(
                f"máquina '{nome}' não está declarada em {self.origem}. "
                f"Acrescente a chave em 'maquinas' e rode de novo."
            )
        return Maquina(
            nome=nome,
            usuario=declarada["usuario"],
            casa=declarada["casa"],
            sistema=declarada["sistema"],
        )


def ler(caminho: Path) -> Manifesto:
    caminho = Path(caminho)
    with caminho.open(encoding="utf-8") as arquivo:
        return Manifesto(origem=caminho, dados=json.load(arquivo))
