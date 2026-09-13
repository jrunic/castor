"""As checagens que o usuário declara, e o que cada uma conclui.

Sem limiar, janela ou linha de base inventados pelo castor: quem declara o que
conta como "bem" é quem opera a máquina. O que esta camada faz é transformar a
resposta crua de cada checagem num resultado com nome, situação e detalhe — e
isso se testa sem máquina nenhuma.
"""
import json
from dataclasses import dataclass
from pathlib import Path

TIPOS = ("comando", "servico", "expiracao")


class ChecagemInvalida(Exception):
    pass


@dataclass(frozen=True)
class Resultado:
    nome: str
    passou: bool
    detalhe: str


def conferir_declaracao(nome: str, declarada: dict) -> str:
    tipo = declarada.get("tipo")
    if not tipo:
        raise ChecagemInvalida(
            f"a checagem '{nome}' não declara 'tipo'. Use um de: "
            f"{', '.join(TIPOS)}.")
    if tipo not in TIPOS:
        raise ChecagemInvalida(
            f"a checagem '{nome}' é do tipo '{tipo}', que não existe. "
            f"Use um de: {', '.join(TIPOS)}.")
    if not declarada.get("maquina"):
        raise ChecagemInvalida(f"a checagem '{nome}' não declara 'maquina'.")
    if tipo == "comando" and not declarada.get("comando"):
        raise ChecagemInvalida(
            f"a checagem '{nome}' é do tipo comando e não declara 'comando'.")
    if tipo == "servico" and not declarada.get("servico"):
        raise ChecagemInvalida(
            f"a checagem '{nome}' é do tipo servico e não declara 'servico'.")
    return tipo


def avaliar_comando(nome: str, saida_codigo: int, texto: str) -> Resultado:
    if saida_codigo == 0:
        return Resultado(nome=nome, passou=True, detalhe="")
    return Resultado(nome=nome, passou=False,
                     detalhe=f"saiu {saida_codigo}: {texto.strip()[:200]}")


def avaliar_servico(nome: str, situacao: str) -> Resultado:
    if situacao == "active":
        return Resultado(nome=nome, passou=True, detalhe="")
    return Resultado(nome=nome, passou=False,
                     detalhe=f"está '{situacao or 'vazio'}'")


def avaliar_expiracao(maquina: str, expiracao) -> Resultado:
    """Expiração desativada é None. Qualquer data é uma contagem regressiva."""
    if expiracao is None:
        return Resultado(nome=f"expiracao:{maquina}", passou=True, detalhe="")
    return Resultado(
        nome=f"expiracao:{maquina}", passou=False,
        detalhe=f"a chave de nó de '{maquina}' expira em {expiracao}; quando "
                f"isso acontecer a máquina sai da rede e o acesso vai junto")


def maquina_inalcancavel(maquina: str, declaradas: dict, motivo: str) -> list:
    """Máquina fora do ar é UMA falha, não uma por checagem dela.

    Sem isto, uma máquina desligada manda um e-mail por checagem declarada — e
    quem recebe cinco e-mails sobre o mesmo problema aprende a ignorar os cinco.
    """
    return [Resultado(nome=f"maquina:{maquina}", passou=False,
                      detalhe=f"{motivo} ({len(declaradas)} checagens não "
                              f"avaliadas)")]


def gravar(arquivo: Path, resultados: list, agora: float) -> Path:
    """Grava ao lado e troca, como o manifesto."""
    destino = Path(arquivo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {"quando": agora,
                "resultados": [{"nome": r.nome, "passou": r.passou,
                                "detalhe": r.detalhe} for r in resultados]}
    ao_lado = destino.with_name(destino.name + ".novo")
    ao_lado.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    ao_lado.replace(destino)
    return destino


def ultima(arquivo: Path):
    caminho = Path(arquivo)
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def _falhas(resultados) -> set:
    """Aceita Resultado e o dicionário lido do arquivo.

    A comparação sempre atravessa uma volta por JSON — de um lado o que acabou
    de rodar, do outro o que ficou gravado.
    """
    if resultados is None:
        return set()
    nomes = set()
    for item in resultados:
        if isinstance(item, Resultado):
            nome, passou = item.nome, item.passou
        else:
            nome, passou = item["nome"], item["passou"]
        if not passou:
            nomes.add(nome)
    return nomes


def piorou(antes, agora) -> list:
    """Quem falha agora e não falhava antes. É isto que dispara aviso.

    Sem ronda anterior, tudo que falha conta como piora: é a primeira notícia
    que o usuário tem.
    """
    return sorted(_falhas(agora) - _falhas(antes))


def melhorou(antes, agora) -> list:
    """Quem falhava e voltou. Quem recebeu o aviso de falha precisa saber."""
    return sorted(_falhas(antes) - _falhas(agora))
