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


RESPOSTA_DA_SONDA = (
    "usuario=castor\ncasa=/home/castor\nsistema=Linux\n"
    "epoca=1789000000\nfuso=-0400\npython=Python 3.14.0\nsudo=sim\n"
)


def _sondar_falso(texto=RESPOSTA_DA_SONDA, codigo=0):
    def executar(destino, comando, **k):
        return conexao.Saida(codigo=codigo, texto=texto, erro="")
    return executar


def test_adicionar_mede_e_grava_sem_perguntar(tmp_path, monkeypatch):
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    monkeypatch.setattr(conexao, "executar", _sondar_falso())

    assert principal(["--manifesto", str(caminho), "maquina", "adicionar",
                      "represa", "--endereco", "represa.exemplo.test",
                      "--usuario", "castor"]) == 0

    gravado = json.loads(caminho.read_text(encoding="utf-8"))["maquinas"]["represa"]
    assert gravado == {"papel": "cliente", "usuario": "castor",
                       "casa": "/home/castor", "sistema": "linux",
                       "endereco": "represa.exemplo.test", "python": "3.14.0"}


def test_adicionar_a_principal_mede_a_propria_maquina(tmp_path):
    from pathlib import Path
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    assert principal(["--manifesto", str(caminho), "maquina", "adicionar",
                      "bancada", "--principal"]) == 0
    gravado = json.loads(caminho.read_text(encoding="utf-8"))["maquinas"]["bancada"]
    assert gravado["papel"] == "principal"
    assert gravado["casa"] == str(Path.home())
    assert gravado["endereco"] == ""


def test_cliente_sem_endereco_nao_e_cadastrada(tmp_path, capsys):
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    assert principal(["--manifesto", str(caminho), "maquina", "adicionar",
                      "represa"]) == 1
    assert "--endereco" in capsys.readouterr().err
    assert json.loads(caminho.read_text(encoding="utf-8"))["maquinas"] == {}


def test_adicionar_reclama_quando_o_relogio_esta_fora(tmp_path, capsys, monkeypatch):
    from castor import medicao as mod_medicao
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    monkeypatch.setattr(conexao, "executar", _sondar_falso())
    monkeypatch.setattr(mod_medicao, "conferir_relogio",
                        lambda medido, agora, **k: "o relógio está fora")
    assert principal(["--manifesto", str(caminho), "maquina", "adicionar",
                      "represa", "--endereco", "represa.exemplo.test"]) == 0
    assert "relógio está fora" in capsys.readouterr().err


def test_adicionar_maquina_ja_declarada_pede_substituir(manifesto, capsys,
                                                        monkeypatch):
    monkeypatch.setattr(conexao, "executar", _sondar_falso())
    assert principal(["--manifesto", str(manifesto), "maquina", "adicionar",
                      "represa", "--endereco", "represa.exemplo.test"]) == 1
    assert "--substituir" in capsys.readouterr().err


def test_adicionar_com_maquina_inalcancavel_devolve_o_codigo_da_rede(tmp_path,
                                                                    monkeypatch):
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")

    def explodir(destino, comando, **k):
        return conexao.Saida(codigo=255, texto="",
                             erro="ssh: Could not resolve hostname represa")
    monkeypatch.setattr(conexao, "executar", explodir)
    assert principal(["--manifesto", str(caminho), "maquina", "adicionar",
                      "represa", "--endereco", "represa.exemplo.test"]) == 2
    assert json.loads(caminho.read_text(encoding="utf-8"))["maquinas"] == {}


def test_listar_mostra_papel_endereco_e_sistema(manifesto, capsys):
    assert principal(["--manifesto", str(manifesto), "maquina", "listar"]) == 0
    saida = capsys.readouterr().out
    assert "bancada" in saida and "principal" in saida
    assert "represa.exemplo.test" in saida


def test_remover_tira_do_manifesto_e_avisa_o_que_fica_para_tras(manifesto, capsys):
    assert principal(["--manifesto", str(manifesto), "maquina", "remover",
                      "represa"]) == 0
    assert "represa" not in json.loads(
        manifesto.read_text(encoding="utf-8"))["maquinas"]
    assert "não desfaz" in capsys.readouterr().out
