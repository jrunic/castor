import re

from castor.manifesto import ErroDeManifesto, Maquina

MARCA = re.compile(r"%\{([A-Z_]+)\}")


class MarcaDesconhecida(ErroDeManifesto):
    pass


def expandir(modelo: str, maquina: Maquina) -> str:
    valores = {
        "CASA": maquina.casa,
        "USUARIO": maquina.usuario,
        "MAQUINA": maquina.nome,
        "SISTEMA": maquina.sistema,
    }

    def trocar(achado: re.Match) -> str:
        nome = achado.group(1)
        if nome not in valores:
            raise MarcaDesconhecida(
                f"marca '%{{{nome}}}' não existe. Conhecidas: {', '.join(sorted(valores))}."
            )
        return valores[nome]

    return MARCA.sub(trocar, modelo)
