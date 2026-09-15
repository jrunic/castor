"""A rede privada, pelo CLI do tailscale.

Sem credencial de API e sem cliente OAuth: a conexão de uma máquina nova sai por
uma URL de login que o comando imprime e que o usuário abre no navegador da
máquina principal, onde já está autenticado.

Medição de 13/09/2026, e ela manda no desenho deste módulo: o bloco 'Self' do
'tailscale status --json' NÃO traz o campo KeyExpiry, nem quando a expiração
está ativa — o 'debug netmap' também não. A expiração de uma máquina só é
legível na entrada de PEER que as outras máquinas enxergam. Por isso a
conferência roda na principal, olhando a cliente, e nunca na própria máquina.
"""
import json
import re
import shutil
import socket
import subprocess

URL_DE_LOGIN = re.compile(r"https://login\.tailscale\.com/\S+")


class ErroDeRede(Exception):
    """Base dos erros desta área."""


class NoDesconhecido(ErroDeRede):
    pass


def montar_subida(nome_na_rede: str) -> list[str]:
    return ["tailscale", "up", "--json", "--timeout=20s",
            "--hostname", nome_na_rede]


def extrair_url_de_login(texto: str) -> str | None:
    bruto = texto.strip()
    try:
        dados = json.loads(bruto)
        url = dados.get("AuthURL") if isinstance(dados, dict) else None
        if url:
            return url
    except json.JSONDecodeError:
        pass
    achado = URL_DE_LOGIN.search(texto)
    return achado.group(0).rstrip('",') if achado else None


def _peer(texto_json: str, nome_na_rede: str) -> dict:
    dados = json.loads(texto_json)
    procurado = nome_na_rede.rstrip(".")
    for par in (dados.get("Peer") or {}).values():
        rede = (par.get("DNSName") or "").rstrip(".")
        nomes = {par.get("HostName", ""), rede, rede.split(".")[0]}
        if procurado in nomes:
            return par
    raise NoDesconhecido(
        f"o nó '{nome_na_rede}' não aparece na rede privada desta máquina. "
        f"Se ele é a própria máquina, a leitura está errada: um nó não enxerga "
        f"a própria expiração. Rode a conferência a partir da principal."
    )


def expiracao_de(texto_json: str, nome_na_rede: str) -> str | None:
    """Devolve a data de expiração da chave de nó, ou None se está desativada."""
    return _peer(texto_json, nome_na_rede).get("KeyExpiry") or None


def esta_online(texto_json: str, nome_na_rede: str) -> bool:
    return bool(_peer(texto_json, nome_na_rede).get("Online"))


def esta_rodando(texto_json: str) -> bool:
    """A própria máquina está conectada à rede privada?

    Diferente de expiracao_de e esta_online, que leem a entrada de peer: aqui é
    o estado do serviço local, e é o que a cliente consegue responder sobre si.
    """
    try:
        return json.loads(texto_json).get("BackendState") == "Running"
    except (json.JSONDecodeError, AttributeError, TypeError):
        return False


def instalar_cliente(*, sistema: str, executor, tem_sudo: bool, which=shutil.which) -> None:
    if not tem_sudo:
        raise ErroDeRede("preciso de sudo uma vez para instalar o Tailscale.")
    if sistema == "darwin":
        executor(["curl", "-fsSL", "-o", "/tmp/tailscale.pkg",
                  "https://pkgs.tailscale.com/stable/tailscale-latest.pkg"])
        executor(["sudo", "installer", "-pkg", "/tmp/tailscale.pkg", "-target", "/"])
        return
    if sistema == "linux":
        if not which("apt-get"):
            raise ErroDeRede("não achei apt-get. Instale o Tailscale e rode de novo.")
        executor(["sudo", "apt-get", "install", "-y", "tailscale"])
        return
    raise ErroDeRede(f"não sei instalar Tailscale em {sistema}.")


def garantir_na_principal(*, sistema, which, executor, tem_sudo, esperar_login) -> None:
    binario = which("tailscale")
    if not binario:
        instalar_cliente(sistema=sistema, executor=executor, tem_sudo=tem_sudo,
                         which=which)
        binario = which("tailscale")
        if not binario:
            raise ErroDeRede(
                "instalei o Tailscale mas o comando nao apareceu no PATH.")
    estado = executor([binario, "status", "--json"], capture_output=True, text=True)
    if esta_rodando(estado.stdout):
        return
    cmd_up = montar_subida(socket.gethostname())
    if sistema == "linux" and tem_sudo:
        cmd_up = ["sudo", *cmd_up]
    try:
        saida_up = executor(cmd_up, capture_output=True, text=True, timeout=20)
        texto = (saida_up.stdout or "") + (saida_up.stderr or "")
    except subprocess.TimeoutExpired as erro:
        stdout = erro.stdout or ""
        stderr = erro.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        texto = stdout + stderr
    url = extrair_url_de_login(texto)
    if not url:
        raise ErroDeRede("o tailscale up nao deu URL de login.")
    esperar_login(url)
    estado = executor([binario, "status", "--json"], capture_output=True, text=True)
    if not esta_rodando(estado.stdout):
        raise ErroDeRede("o Tailscale nao ficou em Running depois do login.")
