import shutil
import socket
import sys
from pathlib import Path

import castor
from castor import chaves as mod_chaves
from castor import manifesto as mod_manifesto
from castor import medicao as mod_medicao
from castor.cadastro import origem_para_gravar
from castor.rede import ErroDeRede

entrada = sys.stdin


class EsgotouPergunta(Exception):
    pass


def _sonda_padrao() -> str | None:
    from castor import rede as mod_rede
    return mod_rede.achar_binario(which=shutil.which)


def _perguntar(pergunta: str, *, validar, default: str | None = None,
               esperado: str = "uma resposta válida") -> str:
    dica = f" [Enter = {default}]" if default is not None else ""
    for tentativa in range(3):
        print(f"{pergunta}{dica}", flush=True)
        linha = entrada.readline()
        if linha == "":
            raise EOFError(f"entrada acabou em: {pergunta}")
        resposta = linha.strip()
        if not resposta and default is not None:
            return default
        valido = validar(resposta)
        if valido is not None:
            return valido
        if tentativa < 2:
            print(f"  esperava: {esperado}", flush=True)
    raise EsgotouPergunta(f"três respostas inválidas em: {pergunta}")


def cabecalho() -> None:
    print("castor configurar — prepara esta máquina como principal")
    print(f"Castor by Orlando Ferreira v{castor.__version__}")
    print("Vou fazer 3 perguntas. Só ajo depois de você confirmar a prévia:")
    print("nada é gravado, nada é instalado antes disso. Ctrl+C cancela.\n")


def _validar_sim_nao(resposta: str) -> str | None:
    r = resposta.lower()
    if r in ("s", "sim"):
        return "s"
    if r in ("n", "não", "nao"):
        return "n"
    return None


def _validar_provedor(resposta: str) -> str | None:
    r = resposta.lower()
    if r in ("g", "google"):
        return "g"
    if r in ("o", "outro"):
        return "o"
    return None


def _validar_intencao_chave(resposta: str) -> str | None:
    r = resposta.strip()
    if r == "c":
        return "c"
    caminho = Path(r).expanduser()
    if caminho.is_file() and Path(str(caminho) + ".pub").is_file():
        return str(caminho)
    return None


def _validar_porta(resposta: str) -> int | None:
    try:
        return int(resposta)
    except ValueError:
        return None


def _validar_nao_vazio(resposta: str) -> str | None:
    return resposta if resposta.strip() else None


def _confirmar(resposta: str) -> str | None:
    r = resposta.lower()
    if r in ("", "s", "sim"):
        return "s"
    if r in ("n", "não", "nao"):
        return "n"
    return None


def _perguntar_smtp() -> dict | None:
    quer = _perguntar("aviso por e-mail?", validar=_validar_sim_nao,
                      default="n", esperado="s ou n")
    if quer != "s":
        return None
    provedor = _perguntar("provedor: Google ou outro?",
                          validar=_validar_provedor,
                          esperado="g (Google) ou o (outro)")
    if provedor == "g":
        print("senha de app: https://myaccount.google.com/apppasswords")
        email = _perguntar("e-mail:", validar=_validar_nao_vazio,
                           esperado="um e-mail")
        senha = _perguntar("senha de app:", validar=_validar_nao_vazio,
                           esperado="a senha de 16 letras do Google")
        return {
            "servidor": "smtp.gmail.com", "porta": 587, "usuario": email,
            "de": email, "para": email, "senha": senha,
        }
    servidor = _perguntar("servidor SMTP:", validar=_validar_nao_vazio,
                          esperado="o endereço do servidor (ex.: smtp.exemplo.test)")
    porta = _perguntar("porta:", validar=_validar_porta, default="587",
                       esperado="um número (ex.: 587)")
    usuario = _perguntar("usuário:", validar=_validar_nao_vazio,
                         esperado="o usuário de login no SMTP")
    senha = _perguntar("senha:", validar=_validar_nao_vazio,
                       esperado="a senha (não vai aparecer na tela)")
    de = _perguntar("remetente", validar=lambda r: r or None, default=usuario,
                    esperado="um e-mail") or usuario
    para = _perguntar("destinatário", validar=lambda r: r or None, default=de,
                      esperado="um e-mail") or de
    return {
        "servidor": servidor, "porta": porta, "usuario": usuario,
        "de": de, "para": para, "senha": senha,
    }


def garantir_rede(**_):
    import os
    import platform
    import subprocess
    from castor import rede as mod_rede
    sistema = "darwin" if platform.system() == "Darwin" else platform.system().lower()
    tem_sudo = os.geteuid() == 0 or bool(shutil.which("sudo"))

    def which(nome):
        if nome == "tailscale":
            return mod_rede.achar_binario(which=shutil.which)
        return shutil.which(nome)

    def esperar(url):
        print(f"abra no navegador: {url}")
    mod_rede.garantir_na_principal(
        sistema=sistema, which=which, executor=subprocess.run,
        tem_sudo=tem_sudo, esperar_login=esperar)


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


def montar_plano(chave: str, nome: str, smtp: dict | None, cadastro: Path,
                 *, sonda_binario=None, quer_node: bool = False) -> dict:
    destino = origem_para_gravar(cadastro) if cadastro.name == "castor.json" else cadastro
    nova = chave == "c"
    return {
        "chave": mod_chaves.caminho_padrao() if nova else Path(chave),
        "chave_nova": nova,
        "nome": nome,
        "smtp": smtp,
        "cadastro": destino,
        "node": quer_node,
        "instalar_tailscale": (sonda_binario or _sonda_padrao)() is None,
    }


def previa(plano: dict) -> list[str]:
    linhas = []
    if plano["chave_nova"]:
        linhas.append(f"criar a chave de acesso em {plano['chave']}")
    else:
        linhas.append(f"adotar a chave em {plano['chave']}")
    linhas.append(f"cadastrar '{plano['nome']}' como principal, "
                  f"no cadastro {plano['cadastro']}")
    if plano["smtp"]:
        linhas.append(f"gravar o cofre com {len(plano['smtp'])} chaves SMTP "
                      "(a senha nunca aparece na tela)")
        linhas.append("ligar o aviso por e-mail")
    if plano["node"]:
        linhas.append("instalar Node 22 LTS no XDG (baixando o instalador "
                      "da release, com a soma conferida)")
    if plano["instalar_tailscale"]:
        linhas.append("instalar o Tailscale, pedindo sudo uma vez")
    return linhas


def rodar(cadastro: Path, *, sonda_binario=None) -> int:
    cabecalho()
    try:
        chave_escolha = _perguntar(
            "chave: criar nova ou caminho da existente",
            validar=_validar_intencao_chave, default="c",
            esperado="'c' ou um caminho com a .pub ao lado")
        nome = _perguntar("nome da máquina", validar=_validar_nao_vazio,
                          default=socket.gethostname(),
                          esperado="um nome (o que está no hostname serve)")
        smtp = _perguntar_smtp()
        quer_node = _perguntar("instalar Node 22 LTS?", validar=_validar_sim_nao,
                               default="n", esperado="s ou n") == "s"
    except EOFError as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except EsgotouPergunta as erro:
        print(f"a configuração não terminou: {erro}", file=sys.stderr)
        return 1

    plano = montar_plano(chave_escolha, nome, smtp, cadastro,
                         sonda_binario=sonda_binario, quer_node=quer_node)
    print("\nVou fazer:\n" + "\n".join(f"  - {linha}" for linha in previa(plano)))
    try:
        confirma = _perguntar("confirma?", validar=_confirmar,
                              default="s", esperado="Enter para sim, 'n' para cancelar")
    except EOFError as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except EsgotouPergunta as erro:
        print(f"a configuração não terminou: {erro}", file=sys.stderr)
        return 1
    if confirma == "n":
        print("cancelado — nada foi feito.")
        return 1

    try:
        garantir_rede()
    except ErroDeRede as erro:
        print(f"a configuração não terminou: {erro}", file=sys.stderr)
        return 1

    if plano.get("node"):
        from castor import runtime as mod_runtime
        try:
            irmao = mod_runtime.baixar_irmao("node")
        except mod_runtime.ErroDeRuntime as erro:
            print(f"a configuração não terminou: {erro}", file=sys.stderr)
            return 1
        import subprocess
        feito = subprocess.run(["sh", str(irmao)], capture_output=True, text=True)
        if feito.returncode != 0:
            print(f"a configuração não terminou: o instalador do Node falhou: "
                  f"{feito.stderr.strip()}", file=sys.stderr)
            return 1
        print(f"Node instalado em {feito.stdout.strip()}")

    try:
        if plano["chave_nova"]:
            privada = mod_chaves.criar(plano["chave"])
        else:
            privada = mod_chaves.adotar(plano["chave"])
    except mod_chaves.ErroDeChave as erro:
        print(f"a configuração não terminou: {erro}", file=sys.stderr)
        return 1
    import getpass
    import platform
    import time
    medido = mod_medicao.Medicao(
        usuario=getpass.getuser(), casa=str(Path.home()),
        sistema=platform.system().lower(), epoca=int(time.time()),
        fuso=time.strftime("%z"), python=platform.python_version(), sudo=False,
    )
    destino = plano["cadastro"]
    lido = mod_manifesto.ler_ou_vazio(destino)
    lido = mod_manifesto.anotar(lido, "chave", str(privada))
    if plano["smtp"]:
        smtp = plano["smtp"]
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
        nome=plano["nome"], usuario=medido.usuario, casa=medido.casa,
        sistema=medido.sistema, papel="principal", python=medido.python,
    )
    from dataclasses import replace
    lido = replace(lido, origem=destino)
    gravado = mod_manifesto.gravar(mod_manifesto.acrescentar(lido, maquina, substituir=True))
    resumo = ["chave", "cadastro", "rede"]
    if plano["smtp"]:
        resumo.append("aviso por e-mail")
    print(f"principal configurada: {', '.join(resumo)}. "
          f"Cadastro em {gravado}.")
    return 0
