import socket
import sys
from pathlib import Path

from castor import chaves as mod_chaves
from castor import manifesto as mod_manifesto
from castor import medicao as mod_medicao
from castor.cadastro import origem_para_gravar
from castor.rede import ErroDeRede

entrada = sys.stdin


def garantir_rede(**_):
    return None


def _ler(pergunta: str) -> str:
    sys.stdout.write(pergunta)
    sys.stdout.flush()
    return entrada.readline().strip()


def rodar(cadastro: Path) -> int:
    criar = _ler("criar chave (c) ou caminho da existente: ")
    nome = _ler("nome da principal: ") or socket.gethostname()
    _ler("aviso por e-mail (s/n): ")
    try:
        garantir_rede()
    except ErroDeRede as erro:
        print(str(erro), file=sys.stderr)
        return 1
    if criar == "c":
        privada = mod_chaves.criar(mod_chaves.caminho_padrao())
    else:
        privada = mod_chaves.adotar(Path(criar))
    import getpass
    import platform
    import time
    medido = mod_medicao.Medicao(
        usuario=getpass.getuser(), casa=str(Path.home()),
        sistema=platform.system().lower(), epoca=int(time.time()),
        fuso=time.strftime("%z"), python=platform.python_version(), sudo=False,
    )
    destino = origem_para_gravar(cadastro) if cadastro.name == "castor.json" else cadastro
    lido = mod_manifesto.ler_ou_vazio(destino)
    lido = mod_manifesto.anotar(lido, "chave", str(privada))
    maquina = mod_manifesto.Maquina(
        nome=nome, usuario=medido.usuario, casa=medido.casa,
        sistema=medido.sistema, papel="principal", python=medido.python,
    )
    from dataclasses import replace
    lido = replace(lido, origem=destino)
    mod_manifesto.gravar(mod_manifesto.acrescentar(lido, maquina, substituir=True))
    return 0
