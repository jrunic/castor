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
    # A linha do serviço entregue, não o código global: a bancada pode ter
    # outros serviços em outros estados, e isto aqui mede este.
    linha = next(l for l in em_dia.stdout.splitlines() if l.startswith("correio"))
    assert "em dia" in linha, em_dia.stdout
    print(f"estado: {linha}")

    original = Path(COFRE).read_text(encoding="utf-8")
    try:
        Path(COFRE).write_text(
            original.replace("abacaxi-de-mentira", "outra-de-mentira"),
            encoding="utf-8")
        depois = castor("segredos", "estado")
        assert depois.returncode == 8, depois.stdout
        linha = next(l for l in depois.stdout.splitlines()
                     if l.startswith("correio"))
        assert "desatualizado" in linha, depois.stdout
        print(f"depois de mexer no cofre: {linha}")
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


@entrega
def test_o_servico_esta_de_pe_com_o_linger_ligado(destino):
    """Duas medições, e nenhuma sozinha prova o que interessa.

    O QUE ESTE TESTE NÃO PROVA: que o serviço sobrevive ao gerenciador de
    usuário sendo derrubado. Provar isso exigiria terminar a sessão do usuário
    na máquina, destrutivo demais para teste automatizado. O que ele prova são
    as duas condições necessárias — serviço ativo e linger ligado, que é o
    mecanismo pelo qual ele sobrevive.
    """
    instalado = castor("servico", "instalar", "vigia", "--maquina", MAQUINA)
    assert instalado.returncode == 0, instalado.stderr
    print(f"\ninstalado: {instalado.stdout.strip()}")

    linger = conexao.executar(destino, "loginctl show-user $(id -un) | "
                                       "grep -i linger")
    assert "Linger=yes" in linger.texto, linger.texto

    ativo = conexao.executar(
        destino, conexao.comando_de_servico("is-active vigia.service"))
    assert ativo.texto.strip() == "active", ativo.texto
    print(f"linger: {linger.texto.strip()} | serviço: {ativo.texto.strip()}")


@entrega
def test_a_unit_gerada_passa_no_verificador_do_systemd(destino):
    """Diretiva em seção errada não dá erro — só é ignorada. Quem diz é o systemd."""
    saida = conexao.executar(
        destino, "systemd-analyze verify "
                 "~/.config/systemd/user/vigia.service 2>&1 || true")
    assert "Unknown" not in saida.texto, saida.texto
    print(f"\nsystemd-analyze: {saida.texto.strip() or 'sem queixa'}")


@entrega
def test_segredo_trocado_chega_ao_processo_depois_do_reiniciar():
    """A volta que faltava: trocar no cofre, entregar, reiniciar, e o processo vê."""
    original = Path(COFRE).read_text(encoding="utf-8")
    try:
        Path(COFRE).write_text(
            original.replace("abacaxi-de-mentira", "trocado-de-mentira"),
            encoding="utf-8")
        assert castor("segredos", "enviar", "vigia",
                      "--maquina", MAQUINA).returncode == 0
        reiniciado = castor("servico", "reiniciar", "vigia", "--maquina", MAQUINA)
        assert reiniciado.returncode == 0, reiniciado.stderr
        registro = castor("servico", "registro", "vigia", "--maquina", MAQUINA,
                          "--linhas", "20")
        assert "trocado-de-mentira" in registro.stdout, registro.stdout
        print("\no processo viu o valor novo depois do reiniciar")
    finally:
        Path(COFRE).write_text(original, encoding="utf-8")
        castor("segredos", "enviar", "vigia", "--maquina", MAQUINA)


@entrega
def test_remover_devolve_a_maquina_ao_estado_anterior(destino):
    removido = castor("servico", "remover", "vigia", "--maquina", MAQUINA)
    assert removido.returncode == 0, removido.stderr
    sobrou = conexao.executar(
        destino, "ls ~/.config/systemd/user/ 2>/dev/null; ls ~/.config/castor/")
    assert "vigia.service" not in sobrou.texto
    assert "vigia.env" not in sobrou.texto
    print(f"\ndepois de remover: {sorted(sobrou.texto.split())}")
