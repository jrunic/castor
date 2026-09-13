import json

import pytest

from castor import conexao
from castor.cli import principal


@pytest.fixture
def manifesto(tmp_path):
    caminho = tmp_path / "castor.json"
    caminho.write_text(json.dumps({
        "chave": str(tmp_path / "chave"),
        "maquinas": {
            "bancada": {"papel": "principal", "usuario": "ana",
                        "casa": "/Users/ana", "sistema": "darwin"},
            "represa": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "represa.exemplo.test", "python": "3.14.0"},
        },
    }), encoding="utf-8")
    return caminho


def test_testar_conexao_boa_diz_a_versao(manifesto, capsys, monkeypatch):
    monkeypatch.setattr(conexao, "versao_remota", lambda destino, **k: "0.1.0")
    assert principal(["--manifesto", str(manifesto), "maquina", "testar",
                      "represa"]) == 0
    assert "0.1.0" in capsys.readouterr().out


@pytest.mark.parametrize("erro,codigo,trecho", [
    (conexao.RedeInalcancavel("represa não respondeu"), 2, "não respondeu"),
    (conexao.ChaveRecusada("recusou a chave"), 3, "recusou a chave"),
    (conexao.CastorAusente("o castor não está instalado"), 4, "não está instalado"),
    (conexao.FalhaDeConexao("o ssh falhou"), 5, "o ssh falhou"),
])
def test_cada_fracasso_tem_codigo_e_mensagem_propria(manifesto, capsys, monkeypatch,
                                                     erro, codigo, trecho):
    def explodir(destino, **k):
        raise erro
    monkeypatch.setattr(conexao, "versao_remota", explodir)
    assert principal(["--manifesto", str(manifesto), "maquina", "testar",
                      "represa"]) == codigo
    assert trecho in capsys.readouterr().err


def test_testar_a_principal_e_recusado_com_explicacao(manifesto, capsys):
    assert principal(["--manifesto", str(manifesto), "maquina", "testar",
                      "bancada"]) == 1
    assert "principal" in capsys.readouterr().err


def test_testar_maquina_que_nao_esta_no_manifesto_nomeia_o_comando(manifesto,
                                                                   capsys):
    assert principal(["--manifesto", str(manifesto), "maquina", "testar",
                      "moinho"]) == 1
    assert "maquina adicionar" in capsys.readouterr().err


def test_cliente_sem_endereco_diz_como_consertar(tmp_path, capsys):
    caminho = tmp_path / "castor.json"
    caminho.write_text(json.dumps({"maquinas": {
        "represa": {"papel": "cliente", "usuario": "castor",
                    "casa": "/home/castor", "sistema": "linux"}}}),
        encoding="utf-8")
    assert principal(["--manifesto", str(caminho), "maquina", "testar",
                      "represa"]) == 1
    assert "--endereco" in capsys.readouterr().err
