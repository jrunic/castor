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


COFRE = os.environ.get("CASTOR_COFRE_DE_TESTE")
MANIFESTO = os.environ.get("CASTOR_MANIFESTO_DE_TESTE")
MAQUINA = os.environ.get("CASTOR_MAQUINA_DE_TESTE")

entrega = pytest.mark.skipif(
    not (ALVO and COFRE and MANIFESTO and MAQUINA),
    reason="CASTOR_COFRE_DE_TESTE, _MANIFESTO_DE_TESTE e _MAQUINA_DE_TESTE "
           "não definidos")


def castor(*argumentos):
    import subprocess
    import sys
    return subprocess.run(
        [sys.executable, "-m", "castor", "--manifesto", MANIFESTO, *argumentos],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "src"})


@entrega
def test_entrega_ponta_a_ponta_contra_maquina_real():
    enviado = castor("segredos", "enviar", "correio", "--maquina", MAQUINA)
    assert enviado.returncode == 0, enviado.stderr
    print(f"\nenviado: {enviado.stdout.strip()}")

    em_dia = castor("segredos", "estado")
    assert em_dia.returncode == 0, em_dia.stdout + em_dia.stderr
    assert "em dia" in em_dia.stdout
    print(f"estado: {em_dia.stdout.strip()}")

    original = Path(COFRE).read_text(encoding="utf-8")
    try:
        Path(COFRE).write_text(
            original.replace("abacaxi-de-mentira", "outra-de-mentira"),
            encoding="utf-8")
        depois = castor("segredos", "estado")
        assert depois.returncode == 8, depois.stdout
        assert "desatualizado" in depois.stdout
        print(f"depois de mexer no cofre: {depois.stdout.strip()}")
    finally:
        Path(COFRE).write_text(original, encoding="utf-8")


@entrega
def test_o_cofre_nao_esta_na_cliente(destino):
    saida = conexao.executar(destino, "ls ~/.config/castor/")
    assert "cofre" not in saida.texto
    print(f"\nna cliente: {sorted(saida.texto.split())}")


@entrega
def test_o_segredo_chegou_com_permissao_restrita(destino):
    saida = conexao.executar(destino, "stat -c %a ~/.config/castor/correio.env")
    assert saida.texto.strip() == "600", saida.texto
    print(f"\npermissão do arquivo do serviço: {saida.texto.strip()}")
