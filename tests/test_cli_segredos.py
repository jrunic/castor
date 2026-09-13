import json
import subprocess
import sys


def preparar(tmp_path):
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "maquinas": {"carvalho": {"usuario": "ana", "casa": "/home/ana", "sistema": "linux"}}
    }), encoding="utf-8")
    modelo = tmp_path / "correio.modelo"
    modelo.write_text('SMTP_USUARIO="%{USUARIO}"\n', encoding="utf-8")
    return manifesto, modelo


def executar(tmp_path, *args):
    manifesto, _ = preparar(tmp_path)
    return subprocess.run(
        [sys.executable, "-m", "castor", *args],
        capture_output=True, text=True, cwd="src",
        env={"CASTOR_MANIFESTO": str(manifesto), "PATH": "/usr/bin:/bin"},
    )


def test_gerar_pela_linha_de_comando_escreve_o_arquivo(tmp_path):
    _, modelo = preparar(tmp_path)
    destino = tmp_path / "correio.env"

    saida = executar(tmp_path, "segredos", "gerar", str(modelo),
                     "--maquina", "carvalho", "--destino", str(destino))

    assert saida.returncode == 0, saida.stderr
    assert destino.read_text(encoding="utf-8") == 'SMTP_USUARIO="ana"\n'
    assert "ana" not in saida.stdout


def test_maquina_desconhecida_sai_com_status_e_nomeia_o_manifesto(tmp_path):
    _, modelo = preparar(tmp_path)

    saida = executar(tmp_path, "segredos", "gerar", str(modelo),
                     "--maquina", "cedro", "--destino", str(tmp_path / "x.env"))

    assert saida.returncode == 1
    assert "cedro" in saida.stderr
    assert "castor.json" in saida.stderr
