import json
import subprocess
import sys

import castor
from castor.cli import AREAS, principal


def executar(*args):
    return subprocess.run(
        [sys.executable, "-m", "castor", *args],
        capture_output=True, text=True, cwd="src",
    )


def test_ajuda_da_ronda_nao_fala_seco():
    saida = executar("ronda", "rodar", "--help")
    assert saida.returncode == 0
    assert "--ensaio" in saida.stdout
    assert "--seco" not in saida.stdout


def test_ajuda_lista_as_sete_areas():
    saida = executar("--help")
    assert saida.returncode == 0
    for area in ("chave", "maquina", "segredos", "servico", "rotina", "ronda",
                 "atualizacao"):
        assert area in saida.stdout, f"area ausente na ajuda: {area}"
    assert len(AREAS) == 7


def test_area_desconhecida_falha_com_status():
    saida = executar("inexistente")
    assert saida.returncode != 0


def test_sem_area_nenhuma_mostra_a_ajuda_e_falha():
    saida = executar()
    assert saida.returncode == 1
    assert "castor" in saida.stdout


def test_versao_imprime_so_o_numero(capsys):
    assert principal(["--versao"]) == 0
    assert capsys.readouterr().out.strip() == castor.__version__


def test_chave_mostrar_imprime_a_publica(tmp_path, capsys):
    privada = tmp_path / "castor"
    privada.write_text("PRIVADA\n", encoding="utf-8")
    (tmp_path / "castor.pub").write_text("ssh-ed25519 AAAA... ana\n",
                                         encoding="utf-8")
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({"maquinas": {}, "chave": str(privada)}),
                         encoding="utf-8")

    assert principal(["--manifesto", str(manifesto), "chave", "mostrar"]) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("ssh-ed25519")
    assert "PRIVADA" not in saida


def test_chave_usar_anota_o_caminho_no_manifesto(tmp_path, capsys):
    privada = tmp_path / "minha"
    privada.write_text("PRIVADA\n", encoding="utf-8")
    (tmp_path / "minha.pub").write_text("ssh-ed25519 AAAA... ana\n",
                                        encoding="utf-8")
    manifesto = tmp_path / "castor.json"
    manifesto.write_text('{"maquinas": {}}', encoding="utf-8")

    assert principal(["--manifesto", str(manifesto),
                      "chave", "usar", str(privada)]) == 0
    assert json.loads(manifesto.read_text(encoding="utf-8"))["chave"] == str(privada)


def test_chave_usar_sem_a_publica_ao_lado_falha_sem_sujar_o_manifesto(tmp_path,
                                                                     capsys):
    privada = tmp_path / "minha"
    privada.write_text("PRIVADA\n", encoding="utf-8")
    manifesto = tmp_path / "castor.json"
    manifesto.write_text('{"maquinas": {}}', encoding="utf-8")

    assert principal(["--manifesto", str(manifesto),
                      "chave", "usar", str(privada)]) == 1
    assert "chave" not in json.loads(manifesto.read_text(encoding="utf-8"))
    assert "minha.pub" in capsys.readouterr().err


def test_chave_criar_grava_o_par_e_anota_o_manifesto(tmp_path, capsys):
    manifesto = tmp_path / "castor.json"
    manifesto.write_text('{"maquinas": {}}', encoding="utf-8")
    destino = tmp_path / "chaves" / "castor"

    assert principal(["--manifesto", str(manifesto), "chave", "criar",
                      "--caminho", str(destino)]) == 0
    assert destino.exists()
    saida = capsys.readouterr().out
    assert "ssh-ed25519" in saida
    assert json.loads(manifesto.read_text(encoding="utf-8"))["chave"] == str(destino)


def test_toda_area_lista_os_proprios_verbos():
    """Critério 1 da spec, inteiro: não basta a área aparecer na ajuda.

    Enquanto uma área existia sem verbos, ela aparecia em 'castor --help' e não
    respondia nada — a superfície parecia maior do que era.
    """
    for area in AREAS:
        saida = executar(area, "--help")
        assert saida.returncode == 0, f"{area}: {saida.stderr}"
        assert "verbo" in saida.stdout, f"{area} não lista verbos"
