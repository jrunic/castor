import pytest

from castor import medicao
from castor.medicao import MedicaoIncompleta

RESPOSTA = (
    "usuario=castor\n"
    "casa=/home/castor\n"
    "sistema=Linux\n"
    "epoca=1789000000\n"
    "fuso=-0400\n"
    "python=Python 3.14.0\n"
    "sudo=sim\n"
)


def test_interpreta_os_campos_da_sonda():
    medido = medicao.interpretar(RESPOSTA)
    assert medido.usuario == "castor"
    assert medido.casa == "/home/castor"
    assert medido.sistema == "linux"
    assert medido.epoca == 1789000000
    assert medido.fuso == "-0400"
    assert medido.python == "3.14.0"
    assert medido.sudo is True


def test_sudo_negado_e_lido_como_falso():
    assert medicao.interpretar(RESPOSTA.replace("sudo=sim", "sudo=nao")).sudo is False


def test_python_ausente_vira_vazio_e_nao_explode():
    medido = medicao.interpretar(RESPOSTA.replace("Python 3.14.0", "ausente"))
    assert medido.python == ""


def test_campo_que_nao_veio_e_erro_que_nomeia_o_campo():
    with pytest.raises(MedicaoIncompleta) as erro:
        medicao.interpretar(RESPOSTA.replace("casa=/home/castor\n", ""))
    assert "casa" in str(erro.value)


def test_linha_de_ruido_do_shell_nao_atrapalha():
    medido = medicao.interpretar("Bem-vindo ao servidor!\n" + RESPOSTA)
    assert medido.usuario == "castor"


def test_relogio_muito_fora_e_apontado_com_o_desvio():
    medido = medicao.interpretar(RESPOSTA)
    queixa = medicao.conferir_relogio(medido, agora=1789000600)
    assert queixa is not None
    assert "600" in queixa


def test_relogio_dentro_da_tolerancia_nao_se_queixa():
    medido = medicao.interpretar(RESPOSTA)
    assert medicao.conferir_relogio(medido, agora=1789000030) is None


def test_relogio_adiantado_conta_igual_ao_atrasado():
    medido = medicao.interpretar(RESPOSTA)
    assert medicao.conferir_relogio(medido, agora=1788999400) is not None


def test_python_velho_demais_e_apontado_com_a_versao_minima():
    medido = medicao.interpretar(RESPOSTA.replace("3.14.0", "3.9.6"))
    queixa = medicao.conferir_python(medido)
    assert "3.12" in queixa


def test_python_novo_o_bastante_nao_se_queixa():
    assert medicao.conferir_python(medicao.interpretar(RESPOSTA)) is None


def test_python_ausente_e_apontado_como_ausente():
    medido = medicao.interpretar(RESPOSTA.replace("Python 3.14.0", "ausente"))
    assert "não achei" in medicao.conferir_python(medido)


def test_sonda_cabe_numa_linha_e_nao_usa_aspas_simples():
    """Aspas simples dentro da sonda quebram ao atravessar ssh e shell remoto."""
    assert "\n" not in medicao.SONDA
    assert "'" not in medicao.SONDA


def test_sonda_pergunta_todos_os_campos_que_o_interpretador_exige():
    for campo in medicao.CAMPOS:
        assert f"{campo}=" in medicao.SONDA


def test_fuso_diferente_do_daqui_e_relatado_sem_barrar():
    """Critério 3 pede fuso conferido — mas fuso diferente é normal, não erro."""
    medido = medicao.interpretar(RESPOSTA)
    nota = medicao.conferir_fuso(medido, fuso_daqui="-0300")
    assert nota is not None
    assert "-0400" in nota and "-0300" in nota


def test_mesmo_fuso_nao_gera_nota():
    medido = medicao.interpretar(RESPOSTA)
    assert medicao.conferir_fuso(medido, fuso_daqui="-0400") is None
