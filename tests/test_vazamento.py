import json
import subprocess
import sys

SENHA_SINTETICA = "abacaxi-de-mentira-123"


def _bancada(tmp_path):
    """Cofre, manifesto e arquivo de serviço, todos com a mesma senha."""
    cofre = tmp_path / "cofre"
    cofre.write_text(f"SMTP_SENHA={SENHA_SINTETICA}\n", encoding="utf-8")
    cofre.chmod(0o600)
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "cofre": str(cofre),
        "maquinas": {
            "computador-principal": {"papel": "principal", "usuario": "ana",
                        "casa": str(tmp_path), "sistema": "linux"},
            "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "endereco.invalid"},
        },
        "servicos": {"correio": {"chaves": ["SMTP_SENHA"],
                                 "destino": "$HOME/correio.env"}},
    }), encoding="utf-8")
    env = tmp_path / "correio.env"
    env.write_text(f'SMTP_SENHA="{SENHA_SINTETICA}"\n', encoding="utf-8")
    return manifesto, env


def _rodar(ambiente, *argumentos):
    return subprocess.run(
        [sys.executable, "-m", "castor", *argumentos],
        capture_output=True, text=True, cwd="src", env=ambiente,
    )


def test_nenhum_comando_imprime_segredo(tmp_path):
    manifesto, env = _bancada(tmp_path)
    ambiente = {"CASTOR_CADASTRO": str(manifesto), "PATH": "/usr/bin:/bin"}

    # 'enviar' e 'estado' falham por não alcançar a máquina — e é justamente
    # no caminho de erro que um segredo escapa para a mensagem.
    for argumentos in (
        ["--help"],
        ["segredos", "--help"],
        ["segredos", "ver", str(env), "SMTP_SENHA"],
        ["segredos", "gerar", "correio", "--maquina", "computador-principal"],
        ["segredos", "enviar", "correio", "--maquina", "computador-auxiliar"],
        ["segredos", "estado"],
    ):
        saida = _rodar(ambiente, *argumentos)
        assert SENHA_SINTETICA not in saida.stdout, argumentos
        assert SENHA_SINTETICA not in saida.stderr, argumentos

    # E a flag explícita continua revelando — senão o teste acima passaria
    # mesmo que `ver` estivesse quebrado e não imprimisse nada.
    revelado = _rodar(ambiente, "segredos", "ver", str(env), "SMTP_SENHA",
                      "--revelar")
    assert SENHA_SINTETICA in revelado.stdout


def test_o_arquivo_gerado_tem_a_senha_mas_a_saida_nao(tmp_path):
    """Prova que o comando produziu o segredo — no arquivo, não na tela."""
    manifesto, _ = _bancada(tmp_path)
    ambiente = {"CASTOR_CADASTRO": str(manifesto), "PATH": "/usr/bin:/bin"}
    destino = tmp_path / "gerado.env"
    saida = _rodar(ambiente, "segredos", "gerar", "correio", "--maquina",
                   "computador-principal", "--destino", str(destino))
    assert saida.returncode == 0, saida.stderr
    assert SENHA_SINTETICA in destino.read_text(encoding="utf-8")
    assert SENHA_SINTETICA not in saida.stdout + saida.stderr
