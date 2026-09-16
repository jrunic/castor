import json

import pytest

from castor import rede
from castor.rede import ErroDeRede, NoDesconhecido

STATUS = json.dumps({
    "BackendState": "Running",
    "Self": {"HostName": "computador-principal", "Online": True},
    "Peer": {
        "chave1": {"HostName": "computador-auxiliar", "DNSName": "computador-auxiliar.rede.exemplo.",
                   "Online": True, "KeyExpiry": "2026-12-16T13:48:07Z",
                   "OS": "linux"},
        "chave2": {"HostName": "moinho", "DNSName": "moinho.rede.exemplo.",
                   "Online": False, "KeyExpiry": None, "OS": "linux"},
        "chave3": {"HostName": "acude", "DNSName": "acude.rede.exemplo.",
                   "Online": True, "OS": "linux"},
    },
})

SUBIDA = (
    "\nTo authenticate, visit:\n\n"
    "\thttps://login.tailscale.com/a/1a2b3c4d5e6f\n\n"
)


def test_extrai_a_url_de_login_que_o_comando_imprimiu():
    assert rede.extrair_url_de_login(SUBIDA) == \
        "https://login.tailscale.com/a/1a2b3c4d5e6f"


def test_extrai_authurl_do_json_sem_tty():
    texto = json.dumps({
        "AuthURL": "https://login.tailscale.com/a/64f6fd201296d",
        "BackendState": "NeedsLogin",
    })
    assert rede.extrair_url_de_login(texto) == \
        "https://login.tailscale.com/a/64f6fd201296d"


def test_sem_url_devolve_nada_em_vez_de_inventar():
    assert rede.extrair_url_de_login("Success.") is None


def test_subida_leva_o_nome_da_maquina():
    assert rede.montar_subida("computador-auxiliar") == [
        "tailscale", "up", "--json", "--timeout=20s",
        "--hostname", "computador-auxiliar"]


def test_expiracao_ativa_e_lida_na_entrada_de_peer():
    assert rede.expiracao_de(STATUS, "computador-auxiliar") == "2026-12-16T13:48:07Z"


def test_expiracao_desativada_devolve_nada():
    assert rede.expiracao_de(STATUS, "moinho") is None


def test_campo_ausente_e_campo_nulo_significam_a_mesma_coisa():
    """Medido em 13/09/2026: nó com expiração desativada ora traz null, ora nada."""
    assert rede.expiracao_de(STATUS, "acude") is None


def test_no_que_nao_aparece_no_status_e_erro_nomeado():
    with pytest.raises(NoDesconhecido) as erro:
        rede.expiracao_de(STATUS, "computador-auxiliar-2")
    assert "computador-auxiliar-2" in str(erro.value)


def test_o_proprio_no_nao_serve_para_conferir_a_propria_expiracao():
    """Self nunca traz KeyExpiry — medido em 13/09/2026. Ler dali seria mentir."""
    with pytest.raises(NoDesconhecido) as erro:
        rede.expiracao_de(STATUS, "computador-principal")
    assert "principal" in str(erro.value)


def test_o_no_tambem_e_achado_pelo_nome_de_rede():
    assert rede.expiracao_de(STATUS, "moinho.rede.exemplo.") is None


def test_online_e_lido_da_entrada_de_peer():
    assert rede.esta_online(STATUS, "computador-auxiliar") is True
    assert rede.esta_online(STATUS, "moinho") is False


def test_backend_rodando_e_lido_do_estado_da_propria_maquina():
    assert rede.esta_rodando(STATUS) is True


def test_backend_desligado_nao_passa_por_rodando():
    parado = json.dumps({"BackendState": "NeedsLogin", "Self": {}, "Peer": {}})
    assert rede.esta_rodando(parado) is False


def test_estado_ilegivel_nao_vira_rodando():
    assert rede.esta_rodando("") is False
    assert rede.esta_rodando("isto não é json") is False


class _Saida:
    def __init__(self, codigo=0, stdout="", stderr=""):
        self.returncode = codigo
        self.stdout = stdout
        self.stderr = stderr


def test_instalar_darwin_sem_sudo_recusa():
    with pytest.raises(ErroDeRede) as erro:
        rede.instalar_cliente(sistema="darwin", executor=lambda *a, **k: _Saida(),
                              tem_sudo=False)
    assert "sudo" in str(erro.value)


def test_instalar_darwin_com_soma_divergente_nao_instala():
    """Walter, macOS: a URL 'latest' deu 404; e pkg sem soma conferida não
    ganha sudo installer."""
    chamadas = []

    def executor(cmd, **_):
        chamadas.append(cmd)
        if any("shasum" in str(parte) for parte in cmd):
            return _Saida(codigo=1, stderr="FAILED")
        return _Saida()

    with pytest.raises(ErroDeRede) as erro:
        rede.instalar_cliente(sistema="darwin", executor=executor, tem_sudo=True)
    assert "soma" in str(erro.value)
    assert not any("installer" in c for c in chamadas)


def test_a_url_do_pkg_e_a_versionada_medida():
    assert rede.URL_DO_PKG == ("https://pkgs.tailscale.com/stable/"
                               "Tailscale-1.102.4-macos.pkg")


def test_instalar_linux_sem_apt_recusa():
    with pytest.raises(ErroDeRede) as erro:
        rede.instalar_cliente(
            sistema="linux", executor=lambda *a, **k: _Saida(),
            tem_sudo=True, which=lambda n: None)
    assert "apt" in str(erro.value)


def test_binario_e_achado_no_caminho_da_aplicacao_quando_path_nao_tem():
    """No macOS o Tailscale vive fora do PATH do ssh não-interativo."""

    def existe(caminho):
        return str(caminho).endswith("/Applications/Tailscale.app/Contents/MacOS/Tailscale")

    achado = rede.achar_binario(which=lambda nome: None, existe=existe)
    assert achado == "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


def test_binario_do_path_vence_os_caminhos_conhecidos():
    assert rede.achar_binario(
        which=lambda nome: "/usr/bin/tailscale" if nome == "tailscale" else None,
        existe=lambda caminho: False) == "/usr/bin/tailscale"


def test_o_binario_do_path_e_resolvido_quando_e_symlink(tmp_path):
    """Walter, macOS: CLI via symlink crasha — 'bundleIdentifier is unknown
    to the registry'. Só o caminho real do app é executável."""
    real = tmp_path / "Tailscale.app" / "Contents" / "MacOS" / "Tailscale"
    real.parent.mkdir(parents=True)
    real.write_text("#!/bin/sh\n")
    atalho = tmp_path / "bin" / "tailscale"
    atalho.parent.mkdir(parents=True)
    atalho.symlink_to(real)
    achado = rede.achar_binario(which=lambda n: str(atalho) if n == "tailscale" else None)
    assert achado == str(real)


def test_garantir_com_binario_ja_rodando_nao_instala():
    chamadas = []

    def which(nome):
        return "/usr/bin/tailscale" if nome == "tailscale" else None

    def executor(cmd, **_):
        chamadas.append(cmd)
        return _Saida(stdout=STATUS)

    rede.garantir_na_principal(
        sistema="darwin", which=which, executor=executor, tem_sudo=False,
        esperar_login=lambda url: None)
    assert chamadas == [["/usr/bin/tailscale", "status", "--json"]]


def test_o_up_leva_teto_de_tempo():
    visto = {}
    n = {"status": 0}

    def which(nome):
        return "/usr/bin/tailscale" if nome == "tailscale" else None

    def executor(cmd, **kw):
        if "up" in cmd:
            visto["timeout"] = kw.get("timeout")
            return _Saida(stderr=SUBIDA)
        n["status"] += 1
        if n["status"] == 1:
            return _Saida(stdout='{"BackendState": "NeedsLogin"}')
        return _Saida(stdout=STATUS)

    urls = []
    rede.garantir_na_principal(
        sistema="linux", which=which, executor=executor, tem_sudo=True,
        esperar_login=urls.append)
    assert visto.get("timeout") == 20
    assert urls and urls[0].startswith("https://login.tailscale.com/")
