import shutil
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
    import os
    import platform
    import subprocess
    from castor import rede as mod_rede
    sistema = "darwin" if platform.system() == "Darwin" else platform.system().lower()
    tem_sudo = os.geteuid() == 0 or bool(shutil.which("sudo"))
    def esperar(url):
        print(f"abra no navegador: {url}")
    mod_rede.garantir_na_principal(
        sistema=sistema, which=shutil.which, executor=subprocess.run,
        tem_sudo=tem_sudo, esperar_login=esperar)


def _ler(pergunta: str) -> str:
    print(pergunta, flush=True)
    linha = entrada.readline()
    if linha == "":
        raise EOFError(f"entrada acabou em: {pergunta}")
    return linha.strip()


def _perguntar_smtp() -> dict | None:
    if _ler("aviso por e-mail (s/n): ").lower() not in ("s", "sim"):
        return None
    provedor = _ler("google (g) ou outro (o): ").lower()
    if provedor in ("g", "google"):
        print("senha de app: https://myaccount.google.com/apppasswords")
        email = _ler("e-mail: ")
        senha = _ler("senha de app: ")
        return {
            "servidor": "smtp.gmail.com", "porta": 587, "usuario": email,
            "de": email, "para": email, "senha": senha,
        }
    servidor = _ler("servidor SMTP: ")
    porta = int(_ler("porta: ") or "587")
    usuario = _ler("usuario: ")
    senha = _ler("senha: ")
    de = _ler("remetente (vazio = usuario): ") or usuario
    para = _ler("destinatario (vazio = remetente): ") or de
    return {
        "servidor": servidor, "porta": porta, "usuario": usuario,
        "de": de, "para": para, "senha": senha,
    }


def _gravar_cofre(smtp: dict) -> Path:
    caminho = Path.home() / ".config" / "castor" / "cofre"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = (
        f"SMTP_SERVIDOR={smtp['servidor']}\n"
        f"SMTP_PORTA={smtp['porta']}\n"
        f"SMTP_USUARIO={smtp['usuario']}\n"
        f"SMTP_SENHA={smtp['senha']}\n"
    )
    caminho.write_text(linhas, encoding="utf-8")
    caminho.chmod(0o600)
    return caminho


def rodar(cadastro: Path) -> int:
    try:
        criar = _ler("criar chave (c) ou caminho da existente: ")
        nome = _ler("nome da principal: ") or socket.gethostname()
        smtp = _perguntar_smtp()
    except EOFError as erro:
        print(str(erro), file=sys.stderr)
        return 1
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
    if smtp:
        cofre = _gravar_cofre(smtp)
        env = "$HOME/.config/castor/correio.env"
        lido = mod_manifesto.anotar(lido, "cofre", str(cofre))
        lido = mod_manifesto.anotar(lido, "servicos", {
            "correio": {
                "chaves": ["SMTP_SERVIDOR", "SMTP_PORTA", "SMTP_USUARIO",
                           "SMTP_SENHA"],
                "destino": env,
                "maquinas": [],
            }
        })
        lido = mod_manifesto.anotar(lido, "aviso", {
            "servico": "correio",
            "servidor": smtp["servidor"], "porta": smtp["porta"],
            "usuario": smtp["usuario"], "de": smtp["de"], "para": smtp["para"],
            "janela_em_minutos": 60,
            "arquivo_de_segredo": env, "variavel": "SMTP_SENHA",
        })
    maquina = mod_manifesto.Maquina(
        nome=nome, usuario=medido.usuario, casa=medido.casa,
        sistema=medido.sistema, papel="principal", python=medido.python,
    )
    from dataclasses import replace
    lido = replace(lido, origem=destino)
    mod_manifesto.gravar(mod_manifesto.acrescentar(lido, maquina, substituir=True))
    return 0
