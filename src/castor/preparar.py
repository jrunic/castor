"""O roteiro que leva uma máquina recém-instalada a máquina cliente.

Duas regras estruturais, e as duas existem porque um engano aqui tranca a
máquina do usuário:

1. Todo passo confere o próprio efeito. Um comando que voltou zero afirma sobre
   o processo, não sobre o mundo.
2. Todo passo que fecha um caminho de acesso declara, em 'exige', a prova de
   que o caminho novo funciona. Sem a prova no lugar, o passo não roda.
"""
from dataclasses import dataclass, field
from typing import Callable


class ErroDePreparo(Exception):
    """Base dos erros desta área."""


class PassoNaoProvado(ErroDePreparo):
    pass


class EfeitoNaoConfirmado(ErroDePreparo):
    pass


@dataclass(frozen=True)
class Passo:
    """Um passo do roteiro.

    'conferir' devolve a queixa quando o efeito não apareceu, e nada quando
    apareceu — devolver booleano jogaria fora justamente o que quem lê precisa
    ler ("o relógio está 600 segundos fora", e não "o efeito não apareceu").
    """

    nome: str
    fazer: Callable | None = None
    conferir: Callable | None = None
    exige: tuple[str, ...] = field(default_factory=tuple)
    pendente: str = ""


def executar(passos: list[Passo], contexto: dict, relatar=print) -> list[str]:
    provados: list[str] = []
    for passo in passos:
        if passo.pendente:
            relatar(f"[pendente] {passo.nome}: {passo.pendente}")
            continue
        faltando = [nome for nome in passo.exige if nome not in provados]
        if faltando:
            raise PassoNaoProvado(
                f"o passo '{passo.nome}' fecha um caminho de acesso e exige "
                f"{', '.join(faltando)} — que não foi provado. O roteiro parou "
                f"antes de mexer em qualquer coisa."
            )
        relatar(f"[{passo.nome}] ...")
        if passo.fazer is not None:
            passo.fazer(contexto)
        queixa = passo.conferir(contexto) if passo.conferir is not None else None
        if queixa:
            raise EfeitoNaoConfirmado(
                f"o passo '{passo.nome}' rodou, mas o efeito não apareceu: "
                f"{queixa}. O roteiro parou aqui; a máquina continua acessível "
                f"pelo caminho anterior."
            )
        relatar(f"[{passo.nome}] feito")
        provados.append(passo.nome)
    return provados
