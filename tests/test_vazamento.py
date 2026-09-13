import json
import subprocess
import sys

SENHA_SINTETICA = "abacaxi-de-mentira-123"


def test_nenhum_comando_imprime_segredo(tmp_path):
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "maquinas": {"carvalho": {"usuario": "ana", "casa": str(tmp_path), "sistema": "linux"}}
    }), encoding="utf-8")
    env = tmp_path / "correio.env"
    env.write_text(f'SMTP_SENHA="{SENHA_SINTETICA}"\n', encoding="utf-8")
    ambiente = {"CASTOR_MANIFESTO": str(manifesto), "PATH": "/usr/bin:/bin"}

    for argumentos in (["--help"], ["segredos", "--help"],
                       ["segredos", "ver", str(env), "SMTP_SENHA"]):
        saida = subprocess.run(
            [sys.executable, "-m", "castor", *argumentos],
            capture_output=True, text=True, cwd="src", env=ambiente,
        )
        assert SENHA_SINTETICA not in saida.stdout
        assert SENHA_SINTETICA not in saida.stderr

    # E a flag explícita continua revelando — senão o teste acima passaria
    # mesmo que `ver` estivesse quebrado e não imprimisse nada.
    revelado = subprocess.run(
        [sys.executable, "-m", "castor", "segredos", "ver", str(env), "SMTP_SENHA", "--revelar"],
        capture_output=True, text=True, cwd="src", env=ambiente,
    )
    assert SENHA_SINTETICA in revelado.stdout
