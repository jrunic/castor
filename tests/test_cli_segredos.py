import json

import pytest

from castor.cli import construir_analisador, principal

SENHA_SINTETICA = "abacaxi-de-mentira-123"


@pytest.fixture
def bancada(tmp_path):
    cofre = tmp_path / "cofre"
    cofre.write_text(f"SMTP_SERVIDOR=smtp.exemplo.test\n"
                     f"SMTP_SENHA={SENHA_SINTETICA}\n", encoding="utf-8")
    cofre.chmod(0o600)
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "cofre": str(cofre),
        "chave": str(tmp_path / "chave"),
        "maquinas": {
            "bancada": {"papel": "principal", "usuario": "ana",
                        "casa": str(tmp_path), "sistema": "linux"},
            "represa": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "represa.exemplo.test"},
        },
        "servicos": {"correio": {
            "chaves": ["SMTP_SERVIDOR", "SMTP_SENHA"],
            "destino": "$HOME/.config/castor/correio.env"}},
    }), encoding="utf-8")
    return manifesto


def test_gerar_grava_o_arquivo_do_servico_com_permissao_restrita(bancada,
                                                                 tmp_path,
                                                                 capsys):
    destino = tmp_path / "correio.env"
    assert principal(["--manifesto", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "bancada",
                      "--destino", str(destino)]) == 0
    assert destino.stat().st_mode & 0o077 == 0
    assert SENHA_SINTETICA in destino.read_text(encoding="utf-8")
    assert SENHA_SINTETICA not in capsys.readouterr().out


def test_gerar_sem_destino_recusa_em_vez_de_imprimir(bancada, capsys):
    """O material nunca ensina a imprimir segredo no terminal."""
    assert principal(["--manifesto", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "bancada"]) == 1
    saida = capsys.readouterr()
    assert SENHA_SINTETICA not in saida.out
    assert "--destino" in saida.err


def test_chave_que_falta_no_cofre_nomeia_a_chave(bancada, tmp_path, capsys):
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["servicos"]["correio"]["chaves"].append("TOKEN_AUSENTE")
    bancada.write_text(json.dumps(dados), encoding="utf-8")
    assert principal(["--manifesto", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "bancada",
                      "--destino", str(tmp_path / "x.env")]) == 1
    assert "TOKEN_AUSENTE" in capsys.readouterr().err


def test_cofre_frouxo_recusa_e_nao_grava(bancada, tmp_path, capsys):
    (tmp_path / "cofre").chmod(0o644)
    destino = tmp_path / "correio.env"
    assert principal(["--manifesto", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "bancada",
                      "--destino", str(destino)]) == 1
    assert not destino.exists()
    assert "chmod 600" in capsys.readouterr().err


def test_manifesto_sem_cofre_declarado_diz_o_que_acrescentar(bancada, tmp_path,
                                                             capsys):
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    del dados["cofre"]
    bancada.write_text(json.dumps(dados), encoding="utf-8")
    assert principal(["--manifesto", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "bancada",
                      "--destino", str(tmp_path / "x.env")]) == 1
    assert "'cofre'" in capsys.readouterr().err


def test_o_manifesto_padrao_e_o_da_configuracao_do_usuario(monkeypatch):
    """O cron da cliente não tem diretório de trabalho que alguém controle."""
    monkeypatch.delenv("CASTOR_MANIFESTO", raising=False)
    opcoes = construir_analisador().parse_args(["maquina", "listar"])
    assert opcoes.manifesto.endswith(".config/castor/castor.json")


def test_a_variavel_de_ambiente_continua_mandando(monkeypatch):
    monkeypatch.setenv("CASTOR_MANIFESTO", "/outro/lugar.json")
    opcoes = construir_analisador().parse_args(["maquina", "listar"])
    assert opcoes.manifesto == "/outro/lugar.json"
