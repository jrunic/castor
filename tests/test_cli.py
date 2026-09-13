import subprocess
import sys


def executar(*args):
    return subprocess.run(
        [sys.executable, "-m", "castor", *args],
        capture_output=True, text=True, cwd="src",
    )


def test_ajuda_lista_as_cinco_areas():
    saida = executar("--help")
    assert saida.returncode == 0
    for area in ("segredos", "servico", "rotina", "ronda", "atualizacao"):
        assert area in saida.stdout, f"area ausente na ajuda: {area}"


def test_area_desconhecida_falha_com_status():
    saida = executar("inexistente")
    assert saida.returncode != 0
