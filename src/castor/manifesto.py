import json
from dataclasses import dataclass, replace
from pathlib import Path


class ErroDeManifesto(Exception):
    """Base dos erros desta área."""


class MaquinaDesconhecida(ErroDeManifesto):
    pass


class MaquinaJaDeclarada(ErroDeManifesto):
    pass


class SemPrincipal(ErroDeManifesto):
    pass


@dataclass(frozen=True)
class Maquina:
    nome: str
    usuario: str
    casa: str
    sistema: str
    papel: str = "cliente"
    endereco: str = ""
    python: str = ""

    @property
    def e_principal(self) -> bool:
        return self.papel == "principal"


@dataclass(frozen=True)
class Manifesto:
    origem: Path
    dados: dict

    def maquina(self, nome: str) -> Maquina:
        declarada = self.dados.get("maquinas", {}).get(nome)
        if declarada is None:
            raise MaquinaDesconhecida(
                f"máquina '{nome}' não está declarada em {self.origem}. "
                f"Rode 'castor maquina adicionar {nome} --endereco <endereço>'."
            )
        return Maquina(
            nome=nome,
            usuario=declarada["usuario"],
            casa=declarada["casa"],
            sistema=declarada["sistema"],
            papel=declarada.get("papel", "cliente"),
            endereco=declarada.get("endereco", ""),
            python=declarada.get("python", ""),
        )

    def nomes(self) -> list[str]:
        return sorted(self.dados.get("maquinas", {}))

    def principal(self) -> Maquina:
        for nome in self.nomes():
            maquina = self.maquina(nome)
            if maquina.e_principal:
                return maquina
        raise SemPrincipal(
            f"nenhuma máquina em {self.origem} está declarada como principal. "
            f"Rode 'castor maquina adicionar <nome> --principal' nesta máquina."
        )

    def caminho_da_chave(self) -> Path | None:
        declarado = self.dados.get("chave")
        return Path(declarado).expanduser() if declarado else None


def ler(caminho: Path) -> Manifesto:
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroDeManifesto(
            f"não achei o manifesto em {caminho}. "
            f"Ele nasce no primeiro 'castor maquina adicionar <nome> --principal'."
        )
    with caminho.open(encoding="utf-8") as arquivo:
        return Manifesto(origem=caminho, dados=json.load(arquivo))


def ler_ou_vazio(caminho: Path) -> Manifesto:
    """Para o comando que pode ser o primeiro a rodar numa máquina."""
    caminho = Path(caminho)
    if not caminho.exists():
        return Manifesto(origem=caminho, dados={"maquinas": {}})
    return ler(caminho)


def acrescentar(manifesto: Manifesto, maquina: Maquina,
                *, substituir: bool = False) -> Manifesto:
    declaradas = dict(manifesto.dados.get("maquinas", {}))
    if maquina.nome in declaradas and not substituir:
        raise MaquinaJaDeclarada(
            f"máquina '{maquina.nome}' já está em {manifesto.origem}. "
            f"Use --substituir para remedir e sobrescrever."
        )
    declaradas[maquina.nome] = {
        "papel": maquina.papel,
        "usuario": maquina.usuario,
        "casa": maquina.casa,
        "sistema": maquina.sistema,
        "endereco": maquina.endereco,
        "python": maquina.python,
    }
    return replace(manifesto, dados={**manifesto.dados, "maquinas": declaradas})


def retirar(manifesto: Manifesto, nome: str) -> Manifesto:
    declaradas = dict(manifesto.dados.get("maquinas", {}))
    if nome not in declaradas:
        raise MaquinaDesconhecida(
            f"máquina '{nome}' não está declarada em {manifesto.origem}."
        )
    del declaradas[nome]
    return replace(manifesto, dados={**manifesto.dados, "maquinas": declaradas})


def anotar(manifesto: Manifesto, chave: str, valor) -> Manifesto:
    return replace(manifesto, dados={**manifesto.dados, chave: valor})


def gravar(manifesto: Manifesto) -> Path:
    """Grava ao lado e troca: interrupção não deixa o manifesto pela metade."""
    destino = Path(manifesto.origem)
    destino.parent.mkdir(parents=True, exist_ok=True)
    ao_lado = destino.with_name(destino.name + ".novo")
    texto = json.dumps(manifesto.dados, ensure_ascii=False, indent=2, sort_keys=True)
    ao_lado.write_text(texto + "\n", encoding="utf-8")
    ao_lado.replace(destino)
    return destino
