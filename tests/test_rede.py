import json

import pytest

from castor import rede
from castor.rede import NoDesconhecido

STATUS = json.dumps({
    "BackendState": "Running",
    "Self": {"HostName": "bancada", "Online": True},
    "Peer": {
        "chave1": {"HostName": "represa", "DNSName": "represa.rede.exemplo.",
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


def test_sem_url_devolve_nada_em_vez_de_inventar():
    assert rede.extrair_url_de_login("Success.") is None


def test_subida_leva_o_nome_da_maquina():
    assert rede.montar_subida("represa") == ["tailscale", "up", "--hostname",
                                             "represa"]


def test_expiracao_ativa_e_lida_na_entrada_de_peer():
    assert rede.expiracao_de(STATUS, "represa") == "2026-12-16T13:48:07Z"


def test_expiracao_desativada_devolve_nada():
    assert rede.expiracao_de(STATUS, "moinho") is None


def test_campo_ausente_e_campo_nulo_significam_a_mesma_coisa():
    """Medido em 13/09/2026: nó com expiração desativada ora traz null, ora nada."""
    assert rede.expiracao_de(STATUS, "acude") is None


def test_no_que_nao_aparece_no_status_e_erro_nomeado():
    with pytest.raises(NoDesconhecido) as erro:
        rede.expiracao_de(STATUS, "represa-2")
    assert "represa-2" in str(erro.value)


def test_o_proprio_no_nao_serve_para_conferir_a_propria_expiracao():
    """Self nunca traz KeyExpiry — medido em 13/09/2026. Ler dali seria mentir."""
    with pytest.raises(NoDesconhecido) as erro:
        rede.expiracao_de(STATUS, "bancada")
    assert "principal" in str(erro.value)


def test_o_no_tambem_e_achado_pelo_nome_de_rede():
    assert rede.expiracao_de(STATUS, "moinho.rede.exemplo.") is None


def test_online_e_lido_da_entrada_de_peer():
    assert rede.esta_online(STATUS, "represa") is True
    assert rede.esta_online(STATUS, "moinho") is False
