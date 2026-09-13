"""O que cada serviço de cada máquina recebe do cofre.

'montar' devolve TEXTO, não escreve arquivo. É o que permite o mesmo conteúdo
ser gravado aqui, enviado para a cliente, ou apenas somado para comparação — sem
que o segredo precise passar por disco no caminho.
"""
import hashlib
from pathlib import Path

from castor import cofre as mod_cofre
from castor.manifesto import ErroDeManifesto, Manifesto


class ServicoDesconhecido(ErroDeManifesto):
    pass


class VariavelAusente(ErroDeManifesto):
    pass


def _declarado(manifesto: Manifesto, servico: str) -> dict:
    declarado = manifesto.dados.get("servicos", {}).get(servico)
    if declarado is None:
        raise ServicoDesconhecido(
            f"serviço '{servico}' não está declarado em 'servicos' de "
            f"{manifesto.origem}. Declare as chaves que ele recebe e o destino."
        )
    return declarado


def _casas(manifesto: Manifesto, maquina: str) -> tuple[str, str]:
    return manifesto.maquina(maquina).casa, manifesto.principal().casa


def montar(manifesto: Manifesto, servico: str, maquina: str,
           valores: dict[str, str]) -> str:
    """O conteúdo do arquivo daquele serviço, naquela máquina."""
    declarado = _declarado(manifesto, servico)
    casa, casa_principal = _casas(manifesto, maquina)
    escolhidos = mod_cofre.filtrar(valores, declarado["chaves"],
                                   origem=manifesto.dados.get("cofre", "o cofre"))
    linhas = []
    for chave, valor in escolhidos.items():
        resolvido = mod_cofre.resolver(valor, casa=casa,
                                       casa_principal=casa_principal)
        linhas.append(f'{chave}="{resolvido}"')
    return "\n".join(linhas) + "\n"


def destino_de(manifesto: Manifesto, servico: str, maquina: str) -> str:
    declarado = _declarado(manifesto, servico)
    casa, casa_principal = _casas(manifesto, maquina)
    return mod_cofre.resolver(declarado["destino"], casa=casa,
                              casa_principal=casa_principal)


def soma(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _ler_atribuicoes(arquivo: Path) -> dict[str, str]:
    valores = {}
    for linha in Path(arquivo).read_text(encoding="utf-8").splitlines():
        if "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"')
    return valores


def ver(arquivo: Path, variavel: str, revelar: bool = False) -> str:
    """Por default descreve o segredo; só revela sob pedido explícito."""
    valores = _ler_atribuicoes(arquivo)
    if variavel not in valores:
        raise VariavelAusente(f"variável '{variavel}' não está em {arquivo}.")
    valor = valores[variavel]
    if revelar:
        return valor
    resumo = hashlib.sha256(valor.encode("utf-8")).hexdigest()[:12]
    return f"{variavel}: {len(valor)} caracteres, sha256:{resumo}"
