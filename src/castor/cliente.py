"""O manifesto-da-cliente: só o que diz respeito àquela máquina.

O manifesto inteiro mora na principal e não é copiado. A cliente precisa saber o
que executar — suas rotinas, suas checagens, como avisar — e nada além disso. O
cofre nunca vai, a chave nunca vai, e o endereço da principal nunca vai: a
cliente não acessa a principal, e endereço ali seria convite.
"""
import json

from castor import cofre as mod_cofre
from castor.manifesto import Manifesto

CAMINHO_NA_CLIENTE = ".config/castor/castor.json"


def montar(manifesto: Manifesto, nome: str) -> dict:
    maquina = manifesto.maquina(nome)
    casa_principal = manifesto.principal().casa

    def resolver(valor):
        if isinstance(valor, str):
            return mod_cofre.resolver(valor, casa=maquina.casa,
                                      casa_principal=casa_principal)
        if isinstance(valor, dict):
            return {chave: resolver(item) for chave, item in valor.items()}
        return valor

    rotinas = {
        nome_da_rotina: resolver(declarada)
        for nome_da_rotina, declarada in manifesto.dados.get("rotinas", {}).items()
        if declarada.get("maquina") == nome
    }

    return {
        "maquinas": {nome: {
            "papel": "cliente", "usuario": maquina.usuario,
            "casa": maquina.casa, "sistema": maquina.sistema,
            "endereco": "", "python": maquina.python,
        }},
        "rotinas": rotinas,
        "aviso": resolver(manifesto.dados.get("aviso", {})),
        "ronda": manifesto.dados.get("ronda", {}).get(nome, {}),
    }


def como_texto(manifesto: Manifesto, nome: str) -> str:
    return json.dumps(montar(manifesto, nome), ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"


def destino_na_cliente(manifesto: Manifesto, nome: str) -> str:
    return f"{manifesto.maquina(nome).casa}/{CAMINHO_NA_CLIENTE}"
