import pytest

from castor import atualizacao
from castor.atualizacao import AlvoInvalido


def test_o_castor_se_atualiza_pelo_instalador_de_bootstrap():
    """É o instalador que confere a soma publicada — critério 15."""
    comando = atualizacao.comando_de({"tipo": "castor"})
    assert "instalar.sh" in comando
    assert "curl" in comando


def test_pipx_usa_o_pacote_declarado():
    comando = atualizacao.comando_de({"tipo": "pipx", "pacote": "jd-exemplo"})
    assert comando == "pipx upgrade jd-exemplo"


def test_npm_atualiza_global():
    comando = atualizacao.comando_de({"tipo": "npm", "pacote": "@exemplo/cli"})
    assert "npm" in comando and "-g" in comando and "@exemplo/cli" in comando


def test_comando_declarado_vai_como_esta():
    comando = atualizacao.comando_de({"tipo": "comando",
                                      "comando": "meu-script --atualizar"})
    assert comando == "meu-script --atualizar"


def test_tipo_desconhecido_e_recusado_nomeando_os_que_existem():
    with pytest.raises(AlvoInvalido) as erro:
        atualizacao.comando_de({"tipo": "telepatia"})
    assert "pipx" in str(erro.value) and "castor" in str(erro.value)


def test_pipx_sem_pacote_e_recusado():
    with pytest.raises(AlvoInvalido) as erro:
        atualizacao.comando_de({"tipo": "pipx"})
    assert "pacote" in str(erro.value)


def test_comando_sem_comando_e_recusado():
    with pytest.raises(AlvoInvalido) as erro:
        atualizacao.comando_de({"tipo": "comando"})
    assert "comando" in str(erro.value)


def test_a_pergunta_de_versao_declarada_manda():
    assert atualizacao.comando_de_versao(
        "jd-exemplo", {"versao": "jd-exemplo --version"}) == \
        "jd-exemplo --version"


def test_sem_versao_declarada_pergunta_se_o_comando_responde():
    """Conferir que o gerenciador saiu zero não prova que o programa roda."""
    comando = atualizacao.comando_de_versao("jd-exemplo", {"tipo": "pipx"})
    assert "command -v jd-exemplo" in comando


def test_o_castor_responde_pela_propria_versao():
    comando = atualizacao.comando_de_versao("castor", {"tipo": "castor"})
    assert "castor --versao" in comando


def test_versao_igual_depois_nao_e_falha():
    assert atualizacao.concluir("jd-exemplo", antes="1.0", depois="1.0") == \
        ("sem mudança", True)


def test_versao_diferente_e_atualizacao():
    situacao, passou = atualizacao.concluir("jd-exemplo", antes="1.0",
                                            depois="1.1")
    assert passou and "1.0" in situacao and "1.1" in situacao


def test_comando_que_nao_responde_depois_e_falha():
    situacao, passou = atualizacao.concluir("jd-exemplo", antes="1.0", depois="")
    assert not passou
    assert "não respondeu" in situacao


def test_comando_que_ja_nao_respondia_antes_e_falha_tambem():
    """Alvo declarado e nunca instalado não passa como 'sem mudança'."""
    situacao, passou = atualizacao.concluir("jd-exemplo", antes="", depois="")
    assert not passou


def test_comando_que_passou_a_responder_e_sucesso():
    situacao, passou = atualizacao.concluir("jd-exemplo", antes="", depois="1.0")
    assert passou and "passou a responder" in situacao
