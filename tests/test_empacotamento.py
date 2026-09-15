import subprocess
import sys
import zipfile


def construir(tmp_path):
    alvo = tmp_path / "castor.pyz"
    feito = subprocess.run(
        [sys.executable, "scripts/build-pyz.py", "--saida", str(alvo)],
        capture_output=True, text=True,
    )
    assert feito.returncode == 0, feito.stderr
    return alvo


def test_pacote_roda_e_enumera_as_areas(tmp_path):
    alvo = construir(tmp_path)
    saida = subprocess.run([sys.executable, str(alvo), "--help"], capture_output=True, text=True)
    assert saida.returncode == 0
    assert "segredos" in saida.stdout


def test_pacote_propaga_codigo_de_saida(tmp_path):
    # Manifesto ausente devolve 1. Se o ponto de entrada descartar o retorno,
    # o pacote sai 0 e a falha some.
    #
    # Antes isto media uma "area sem verbos", e a ultima delas ganhou os seus
    # no plano 7 — a cobaia acabou, o invariante nao. Manifesto ausente e uma
    # falha que nao depende de nenhuma area estar incompleta.
    alvo = construir(tmp_path)
    saida = subprocess.run(
        [sys.executable, str(alvo), "--cadastro",
         str(tmp_path / "nao-existe.json"), "maquina", "listar"],
        capture_output=True, text=True)
    assert saida.returncode == 1


def test_pacote_nao_leva_codigo_nativo(tmp_path):
    alvo = construir(tmp_path)
    with zipfile.ZipFile(alvo) as pacote:
        nativos = [n for n in pacote.namelist() if n.endswith((".so", ".pyd", ".dll"))]
    assert nativos == []
