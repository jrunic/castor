import pytest

from castor import unidade
from castor.cofre import ValorHostil
from castor.unidade import DeclaracaoInvalida

DECLARADO = {
    "comando": "$HOME/.local/bin/sentinela --vigiar",
    "descricao": "Sentinela da represa",
    "destino": "$HOME/.config/castor/sentinela.env",
}


def montar(**mudancas):
    return unidade.montar("sentinela", {**DECLARADO, **mudancas},
                          casa="/home/castor", casa_principal="/home/ana")


def test_a_unit_roda_o_comando_com_caminho_resolvido():
    texto = montar()
    assert "ExecStart=/home/castor/.local/bin/sentinela --vigiar" in texto
    assert "$HOME" not in texto


def test_a_unit_carrega_o_arquivo_de_ambiente_que_o_castor_entrega():
    assert "EnvironmentFile=/home/castor/.config/castor/sentinela.env" in montar()


def test_a_unit_e_de_usuario_e_nao_de_sistema():
    texto = montar()
    assert "WantedBy=default.target" in texto
    assert "User=" not in texto
    assert "multi-user.target" not in texto


def test_o_limite_de_reinicio_fica_na_secao_unit():
    """Em [Service] a diretiva é ignorada em silêncio desde o systemd 229."""
    texto = montar()
    # divide no cabeçalho de seção, não em qualquer menção — a seção é a linha
    unit, servico = texto.split("\n[Service]\n")
    assert "StartLimitIntervalSec=" in unit
    assert "StartLimitBurst=" in unit
    assert "StartLimit" not in servico


def test_a_unit_para_em_vez_de_repetir_erro_de_configuracao():
    """78 é EX_CONFIG: o programa disse que a configuração está quebrada."""
    assert "RestartPreventExitStatus=78" in montar()


def test_diretorio_default_e_a_casa_da_maquina():
    assert "WorkingDirectory=/home/castor" in montar()


def test_reiniciar_declarado_manda():
    assert "Restart=always" in montar(reiniciar="always")
    assert "Restart=on-failure" in montar()


def test_reiniciar_desconhecido_e_recusado():
    with pytest.raises(DeclaracaoInvalida) as erro:
        montar(reiniciar="quando-der")
    assert "on-failure" in str(erro.value)


def test_servico_sem_comando_nao_vira_unit():
    with pytest.raises(DeclaracaoInvalida) as erro:
        unidade.montar("correio", {"destino": "/x"}, casa="/c",
                       casa_principal="/p")
    assert "comando" in str(erro.value)


def test_comando_relativo_e_recusado():
    """systemd não procura no PATH e não expande variável em ExecStart."""
    with pytest.raises(DeclaracaoInvalida) as erro:
        montar(comando="sentinela --vigiar")
    assert "absoluto" in str(erro.value)


def test_por_cento_e_recusado_porque_o_systemd_o_expande():
    with pytest.raises(DeclaracaoInvalida) as erro:
        montar(comando="$HOME/bin/x --taxa 50%")
    assert "%" in str(erro.value)


def test_o_comando_pode_referenciar_a_propria_variavel_de_ambiente():
    """É para isso que a entrega de segredo existe.

    O systemd não expande $VAR em ExecStart — passa literal, e quem expande é o
    sh -c que o comando invoca, já com o EnvironmentFile carregado.
    """
    texto = montar(
        comando="/bin/sh -c 'echo vigia com $TOKEN_DA_SENTINELA; exec sleep 86400'")
    assert "$TOKEN_DA_SENTINELA" in texto


def test_cifrao_em_caminho_continua_recusado():
    """Caminho não é comando: ali o cifrão é engano, não referência."""
    with pytest.raises(ValorHostil):
        montar(diretorio="$HOME/$OUTRA")


def test_o_caminho_da_unit_sai_da_casa_medida():
    assert unidade.caminho("/home/castor", "sentinela") == \
        "/home/castor/.config/systemd/user/sentinela.service"
