from dataclasses import dataclass

MARCA = "# castor:{nome}"


@dataclass(frozen=True)
class Agendada:
    nome: str
    quando: str
    comando: str


def _e_do_castor(linha: str, nome: str | None = None) -> bool:
    if nome is not None:
        return linha.rstrip().endswith(MARCA.format(nome=nome))
    return "# castor:" in linha


def agendar_em(tabela: str, nome: str, quando: str, comando: str) -> str:
    """Devolve a tabela com a rotina posta ou substituída.

    Nunca reescreve linha que não seja do castor: a tabela é do usuário, e
    pode ter entradas que vieram de outro lugar.
    """
    linhas = [l for l in tabela.splitlines() if l.strip() and not _e_do_castor(l, nome)]
    linhas.append(f"{quando} {comando} {MARCA.format(nome=nome)}")
    return "\n".join(linhas) + "\n"


def listar_de(tabela: str) -> list[Agendada]:
    achadas = []
    for linha in tabela.splitlines():
        if not _e_do_castor(linha):
            continue
        corpo, _, marca = linha.rpartition("# castor:")
        campos = corpo.split()
        achadas.append(Agendada(
            nome=marca.strip(),
            quando=" ".join(campos[:5]),
            comando=" ".join(campos[5:]),
        ))
    return achadas
