import subprocess

import pytest

from castor import segredos
from castor.manifesto import Maquina

MAQUINA = Maquina(nome="carvalho", usuario="ana", casa="/home/ana", sistema="linux")
SENHA_SINTETICA = "abacaxi-de-mentira-123"


def test_gerar_escreve_uma_atribuicao_por_linha(tmp_path):
    modelo = tmp_path / "correio.modelo"
    modelo.write_text('SMTP_USUARIO="%{USUARIO}"\nSMTP_CASA="%{CASA}"\n', encoding="utf-8")
    destino = tmp_path / "correio.env"

    segredos.gerar(modelo, MAQUINA, destino)

    linhas = destino.read_text(encoding="utf-8").splitlines()
    assert linhas == ['SMTP_USUARIO="ana"', 'SMTP_CASA="/home/ana"']


def test_arquivo_gerado_e_lido_por_shell(tmp_path):
    modelo = tmp_path / "correio.modelo"
    modelo.write_text('SMTP_USUARIO="%{USUARIO}"\n', encoding="utf-8")
    destino = tmp_path / "correio.env"
    segredos.gerar(modelo, MAQUINA, destino)

    lido = subprocess.run(
        ["sh", "-c", f'. {destino} && printf %s "$SMTP_USUARIO"'],
        capture_output=True, text=True,
    )
    assert lido.returncode == 0
    assert lido.stdout == "ana"


def test_valor_com_cifrao_e_recusado(tmp_path):
    modelo = tmp_path / "correio.modelo"
    modelo.write_text('SMTP_SENHA="a$HOME-b"\n', encoding="utf-8")

    with pytest.raises(segredos.ModeloInvalido) as erro:
        segredos.gerar(modelo, MAQUINA, tmp_path / "correio.env")
    assert "SMTP_SENHA" in str(erro.value)


def test_arquivo_gerado_serve_de_environmentfile(tmp_path):
    modelo = tmp_path / "correio.modelo"
    modelo.write_text('SMTP_USUARIO="%{USUARIO}"\n', encoding="utf-8")
    destino = tmp_path / "correio.env"
    segredos.gerar(modelo, MAQUINA, destino)

    for linha in destino.read_text(encoding="utf-8").splitlines():
        assert not linha.startswith("export ")
        assert "$" not in linha
        assert "`" not in linha
        chave = linha.split("=", 1)[0]
        assert chave.replace("_", "").isalnum()


def test_ver_reporta_tamanho_e_soma_sem_o_valor(tmp_path):
    arquivo = tmp_path / "correio.env"
    arquivo.write_text(f'SMTP_SENHA="{SENHA_SINTETICA}"\n', encoding="utf-8")

    relato = segredos.ver(arquivo, "SMTP_SENHA")

    assert SENHA_SINTETICA not in relato
    assert str(len(SENHA_SINTETICA)) in relato
    assert relato.count(":") >= 1


def test_ver_com_revelar_imprime_o_valor(tmp_path):
    arquivo = tmp_path / "correio.env"
    arquivo.write_text(f'SMTP_SENHA="{SENHA_SINTETICA}"\n', encoding="utf-8")

    assert segredos.ver(arquivo, "SMTP_SENHA", revelar=True) == SENHA_SINTETICA
