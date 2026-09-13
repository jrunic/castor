"""Contra máquina real. Pulado a menos que CASTOR_BANCADA aponte uma.

O resto da suíte roda com executor de mentira, e isso prova raciocínio, não
mundo. Aqui a sonda atravessa três shells de verdade — o local, o ssh e o
remoto — e a classificação de fracasso encontra fracassos reais.

Rodar:

    CASTOR_BANCADA=usuario@endereco \\
    CASTOR_CHAVE=~/.ssh/uma-chave \\
    .venv/bin/pytest tests/test_bancada.py -v -s

Cada cenário imprime o que produziu: teste que não exercita nada não é verde,
é ausência de vermelho.
"""
import os
from pathlib import Path

import pytest

from castor import conexao, medicao

ALVO = os.environ.get("CASTOR_BANCADA")

pytestmark = pytest.mark.skipif(not ALVO, reason="CASTOR_BANCADA não definido")


@pytest.fixture
def destino():
    usuario, _, endereco = ALVO.partition("@")
    chave = os.environ.get("CASTOR_CHAVE")
    return conexao.Destino(usuario=usuario, endereco=endereco,
                           chave=Path(chave).expanduser() if chave else None)


def test_a_sonda_atravessa_ssh_e_shell_remoto_inteira(destino):
    saida = conexao.conferir(conexao.executar(destino, medicao.SONDA), destino)
    medido = medicao.interpretar(saida.texto)

    assert medido.usuario
    assert medido.casa.startswith("/")
    assert medido.sistema in ("linux", "darwin")
    assert medido.epoca > 0
    print(f"\nmedido: usuario={medido.usuario} casa={medido.casa} "
          f"sistema={medido.sistema} python={medido.python or 'ausente'} "
          f"sudo={medido.sudo} fuso={medido.fuso}")


def test_o_relogio_da_bancada_bate_com_o_desta_maquina(destino):
    import time
    saida = conexao.conferir(conexao.executar(destino, medicao.SONDA), destino)
    medido = medicao.interpretar(saida.texto)
    queixa = medicao.conferir_relogio(medido, agora=time.time())
    print(f"\nrelógio: {'alinhado' if queixa is None else queixa}")
    assert queixa is None


def test_endereco_que_nao_existe_e_rede_inalcancavel(destino):
    inexistente = conexao.Destino(usuario=destino.usuario,
                                  endereco="nao-existe.invalid",
                                  chave=destino.chave)
    with pytest.raises(conexao.RedeInalcancavel) as erro:
        conexao.conferir(conexao.executar(inexistente, "true"), inexistente)
    print(f"\nrede inalcançável: {erro.value}")


def test_usuario_sem_a_chave_tem_a_chave_recusada(destino):
    sem_acesso = conexao.Destino(usuario="castor-sem-acesso",
                                 endereco=destino.endereco, chave=destino.chave)
    with pytest.raises(conexao.ChaveRecusada) as erro:
        conexao.conferir(conexao.executar(sem_acesso, "true"), sem_acesso)
    print(f"\nchave recusada: {erro.value}")


def test_castor_ausente_e_reconhecido_pelo_que_a_maquina_responde(destino):
    """Antes do preparar, a máquina não tem castor — e o erro tem de dizer isso.

    É aqui que se mede o PATH do ssh não-interativo: um castor instalado em
    ~/.local/bin e invocado sem o PATH corrigido responde igual a um ausente.
    """
    try:
        versao = conexao.versao_remota(destino)
    except conexao.CastorAusente as erro:
        print(f"\ncastor ausente, como esperado antes do preparar: {erro}")
        return
    print(f"\ncastor já instalado nesta bancada: {versao}")
    assert versao
