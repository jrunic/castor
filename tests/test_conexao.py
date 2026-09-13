from pathlib import Path

import pytest

from castor import conexao
from castor.conexao import (
    CastorAusente,
    ChaveRecusada,
    Destino,
    FalhaDeConexao,
    RedeInalcancavel,
    Saida,
)

DESTINO = Destino(usuario="castor", endereco="represa.exemplo.test",
                  chave=Path("/tmp/chave-de-teste"))


def executor_de(codigo=0, saida="", erro=""):
    def executar(comando, **opcoes):
        class Concluido:
            returncode = codigo
            stdout = saida
            stderr = erro
        executar.comando = comando
        executar.opcoes = opcoes
        return Concluido()
    return executar


def test_comando_leva_chave_lote_e_tempo_limite():
    comando = conexao.montar(DESTINO, "id -un")
    assert comando[0] == "ssh"
    assert "BatchMode=yes" in comando
    assert "ConnectTimeout=10" in comando
    assert "/tmp/chave-de-teste" in comando
    assert "IdentitiesOnly=yes" in comando
    assert comando[-2:] == ["castor@represa.exemplo.test", "id -un"]


def test_porta_diferente_da_padrao_entra_no_comando():
    destino = Destino(usuario="castor", endereco="represa.exemplo.test", porta=2222)
    assert "-p" in conexao.montar(destino, "true")


def test_primeiro_acesso_repassa_o_terminal_em_vez_de_capturar():
    comando = conexao.montar(DESTINO, "id -un", com_senha=True)
    assert "BatchMode=no" in comando
    assert "BatchMode=yes" not in comando
    assert "-t" in comando


def test_comando_com_sudo_pede_terminal_mantendo_a_chave():
    """sudo em máquina recém-instalada pede senha, e senha precisa de terminal."""
    comando = conexao.montar(DESTINO, "sudo useradd castor", com_terminal=True)
    assert "-t" in comando
    assert "/tmp/chave-de-teste" in comando


def test_com_terminal_nao_captura_saida():
    """Quem repassa o terminal não lê o que voltou — só o código de saída."""
    executar = executor_de(codigo=0, saida="não deveria chegar aqui")
    saida = conexao.executar(DESTINO, "sudo id", com_terminal=True,
                             executor=executar)
    assert saida.codigo == 0
    assert saida.texto == ""


def test_em_lote_a_saida_volta_inteira():
    executar = executor_de(codigo=0, saida="castor\n")
    saida = conexao.executar(DESTINO, "id -un", executor=executar)
    assert saida.texto == "castor\n"
    assert executar.opcoes.get("capture_output") is True


def test_host_que_nao_resolve_e_rede_inalcancavel():
    saida = Saida(codigo=255, texto="",
                  erro="ssh: Could not resolve hostname represa.exemplo.test")
    with pytest.raises(RedeInalcancavel) as erro:
        conexao.conferir(saida, DESTINO)
    assert "represa.exemplo.test" in str(erro.value)


def test_chave_negada_e_chave_recusada():
    saida = Saida(codigo=255, texto="",
                  erro="castor@represa: Permission denied (publickey).")
    with pytest.raises(ChaveRecusada) as erro:
        conexao.conferir(saida, DESTINO)
    assert "castor chave mostrar" in str(erro.value)


def test_identidade_do_host_mudada_tem_mensagem_propria():
    saida = Saida(codigo=255, texto="", erro="Host key verification failed.")
    with pytest.raises(ChaveRecusada) as erro:
        conexao.conferir(saida, DESTINO)
    assert "identidade" in str(erro.value).lower()


def test_fracasso_255_desconhecido_devolve_o_que_o_ssh_disse():
    saida = Saida(codigo=255, texto="", erro="algo que não catalogamos")
    with pytest.raises(FalhaDeConexao) as erro:
        conexao.conferir(saida, DESTINO)
    assert "algo que não catalogamos" in str(erro.value)


def test_codigo_de_saida_do_comando_remoto_nao_e_fracasso_de_conexao():
    saida = Saida(codigo=2, texto="", erro="grep: sem resultado")
    assert conexao.conferir(saida, DESTINO) is saida


def test_castor_ausente_do_outro_lado_tem_mensagem_propria():
    executar = executor_de(codigo=127, erro="bash: castor: command not found")
    with pytest.raises(CastorAusente) as erro:
        conexao.versao_remota(DESTINO, executor=executar)
    assert "castor maquina preparar" in str(erro.value)


def test_castor_que_responde_com_erro_nao_vira_castor_ausente():
    executar = executor_de(codigo=1, erro="manifesto ilegível")
    with pytest.raises(FalhaDeConexao) as erro:
        conexao.versao_remota(DESTINO, executor=executar)
    assert not isinstance(erro.value, CastorAusente)


def test_versao_remota_devolve_o_numero():
    executar = executor_de(codigo=0, saida="0.1.0\n")
    assert conexao.versao_remota(DESTINO, executor=executar) == "0.1.0"
