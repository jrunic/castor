import subprocess
from pathlib import Path

import pytest

from castor import chaves


class ExecutorFalso:
    """Faz o que o ssh-keygen faria: escreve o par onde mandaram."""

    def __init__(self):
        self.chamadas = []

    def __call__(self, comando, **opcoes):
        self.chamadas.append(comando)
        destino = comando[comando.index("-f") + 1]
        Path(destino).write_text("PRIVADA\n", encoding="utf-8")
        Path(destino + ".pub").write_text("ssh-ed25519 AAAA... castor\n",
                                          encoding="utf-8")

        class Concluido:
            returncode = 0
            stdout = ""
            stderr = ""

        return Concluido()


def test_criar_produz_o_par_no_caminho_pedido(tmp_path):
    executor = ExecutorFalso()
    privada = chaves.criar(tmp_path / "castor", executor=executor)
    assert privada.exists()
    assert chaves.publica_de(privada).exists()
    assert "ed25519" in " ".join(executor.chamadas[0])


def test_criar_nao_sobrescreve_chave_existente(tmp_path):
    (tmp_path / "castor").write_text("CHAVE QUE JÁ ESTAVA AQUI\n", encoding="utf-8")
    with pytest.raises(chaves.ChaveJaExiste):
        chaves.criar(tmp_path / "castor", executor=ExecutorFalso())
    assert (tmp_path / "castor").read_text(encoding="utf-8").startswith("CHAVE QUE")


def test_criar_deixa_a_privada_so_para_o_dono(tmp_path):
    privada = chaves.criar(tmp_path / "castor", executor=ExecutorFalso())
    assert privada.stat().st_mode & 0o077 == 0


def test_adotar_exige_que_a_publica_exista_ao_lado(tmp_path):
    (tmp_path / "minha").write_text("PRIVADA\n", encoding="utf-8")
    with pytest.raises(chaves.ChavePublicaAusente) as erro:
        chaves.adotar(tmp_path / "minha")
    assert "minha.pub" in str(erro.value)


def test_adotar_recusa_chave_que_nao_existe(tmp_path):
    with pytest.raises(chaves.ChaveAusente):
        chaves.adotar(tmp_path / "nao-existe")


def test_adotar_devolve_o_caminho_da_privada(tmp_path):
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-f", str(tmp_path / "minha"), "-N", ""],
        check=True, capture_output=True,
    )
    assert chaves.adotar(tmp_path / "minha") == tmp_path / "minha"


def test_mostrar_imprime_a_publica_e_nunca_a_privada(tmp_path):
    privada = chaves.criar(tmp_path / "castor", executor=ExecutorFalso())
    texto = chaves.mostrar(privada)
    assert texto.startswith("ssh-ed25519")
    assert "PRIVADA" not in texto
