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
            "computador-principal": {"papel": "principal", "usuario": "ana",
                        "casa": "/Users/ana", "sistema": "darwin"},
            "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "computador-auxiliar.exemplo.test", "python": "3.14.0"},
        },
    }), encoding="utf-8")
    return caminho


def test_testar_conexao_boa_diz_a_versao(manifesto, capsys, monkeypatch):
    monkeypatch.setattr(conexao, "versao_remota", lambda destino, **k: "0.1.0")
    assert principal(["--cadastro", str(manifesto), "maquina", "testar",
                      "computador-auxiliar"]) == 0
    assert "0.1.0" in capsys.readouterr().out


@pytest.mark.parametrize("erro,codigo,trecho", [
    (conexao.RedeInalcancavel("computador-auxiliar não respondeu"), 2, "não respondeu"),
    (conexao.ChaveRecusada("recusou a chave"), 3, "recusou a chave"),
    (conexao.CastorAusente("o castor não está instalado"), 4, "não está instalado"),
    (conexao.FalhaDeConexao("o ssh falhou"), 5, "o ssh falhou"),
])
def test_cada_fracasso_tem_codigo_e_mensagem_propria(manifesto, capsys, monkeypatch,
                                                     erro, codigo, trecho):
    def explodir(destino, **k):
        raise erro
    monkeypatch.setattr(conexao, "versao_remota", explodir)
    assert principal(["--cadastro", str(manifesto), "maquina", "testar",
                      "computador-auxiliar"]) == codigo
    assert trecho in capsys.readouterr().err


def test_testar_a_principal_e_recusado_com_explicacao(manifesto, capsys):
    assert principal(["--cadastro", str(manifesto), "maquina", "testar",
                      "computador-principal"]) == 1
    assert "principal" in capsys.readouterr().err


def test_testar_maquina_que_nao_esta_no_manifesto_nomeia_o_comando(manifesto,
                                                                   capsys):
    assert principal(["--cadastro", str(manifesto), "maquina", "testar",
                      "moinho"]) == 1
    assert "maquina adicionar" in capsys.readouterr().err


def test_cliente_sem_endereco_diz_como_consertar(tmp_path, capsys):
    caminho = tmp_path / "castor.json"
    caminho.write_text(json.dumps({"maquinas": {
        "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                    "casa": "/home/castor", "sistema": "linux"}}}),
        encoding="utf-8")
    assert principal(["--cadastro", str(caminho), "maquina", "testar",
                      "computador-auxiliar"]) == 1
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

    assert principal(["--cadastro", str(caminho), "maquina", "adicionar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario", "castor"]) == 0

    gravado = json.loads(caminho.read_text(encoding="utf-8"))["maquinas"]["computador-auxiliar"]
    assert gravado == {"papel": "cliente", "usuario": "castor",
                       "casa": "/home/castor", "sistema": "linux",
                       "endereco": "computador-auxiliar.exemplo.test", "python": "3.14.0"}


def test_adicionar_a_principal_mede_a_propria_maquina(tmp_path):
    from pathlib import Path
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    assert principal(["--cadastro", str(caminho), "maquina", "adicionar",
                      "computador-principal", "--principal"]) == 0
    gravado = json.loads(caminho.read_text(encoding="utf-8"))["maquinas"]["computador-principal"]
    assert gravado["papel"] == "principal"
    assert gravado["casa"] == str(Path.home())
    assert gravado["endereco"] == ""


def test_cliente_sem_endereco_nao_e_cadastrada(tmp_path, capsys):
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    assert principal(["--cadastro", str(caminho), "maquina", "adicionar",
                      "computador-auxiliar"]) == 1
    assert "--endereco" in capsys.readouterr().err
    assert json.loads(caminho.read_text(encoding="utf-8"))["maquinas"] == {}


def test_adicionar_reclama_quando_o_relogio_esta_fora(tmp_path, capsys, monkeypatch):
    from castor import medicao as mod_medicao
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    monkeypatch.setattr(conexao, "executar", _sondar_falso())
    monkeypatch.setattr(mod_medicao, "conferir_relogio",
                        lambda medido, agora, **k: "o relógio está fora")
    assert principal(["--cadastro", str(caminho), "maquina", "adicionar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test"]) == 0
    assert "relógio está fora" in capsys.readouterr().err


def test_adicionar_maquina_ja_declarada_pede_substituir(manifesto, capsys,
                                                        monkeypatch):
    monkeypatch.setattr(conexao, "executar", _sondar_falso())
    assert principal(["--cadastro", str(manifesto), "maquina", "adicionar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test"]) == 1
    assert "--substituir" in capsys.readouterr().err


def test_adicionar_com_maquina_inalcancavel_devolve_o_codigo_da_rede(tmp_path,
                                                                    monkeypatch):
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")

    def explodir(destino, comando, **k):
        return conexao.Saida(codigo=255, texto="",
                             erro="ssh: Could not resolve hostname computador-auxiliar")
    monkeypatch.setattr(conexao, "executar", explodir)
    assert principal(["--cadastro", str(caminho), "maquina", "adicionar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test"]) == 2
    assert json.loads(caminho.read_text(encoding="utf-8"))["maquinas"] == {}


def test_listar_mostra_papel_endereco_e_sistema(manifesto, capsys):
    assert principal(["--cadastro", str(manifesto), "maquina", "listar"]) == 0
    saida = capsys.readouterr().out
    assert "computador-principal" in saida and "principal" in saida
    assert "computador-auxiliar.exemplo.test" in saida


def test_remover_tira_do_manifesto_e_avisa_o_que_fica_para_tras(manifesto, capsys):
    assert principal(["--cadastro", str(manifesto), "maquina", "remover",
                      "computador-auxiliar"]) == 0
    assert "computador-auxiliar" not in json.loads(
        manifesto.read_text(encoding="utf-8"))["maquinas"]
    assert "não desfaz" in capsys.readouterr().out


def _preparo_de_mentira(monkeypatch, *, url=None, expiracao=None,
                        erro_do_roteiro=None):
    """Troca as três fronteiras do preparar: roteiro, tailscale e o Enter."""
    from castor import preparar as mod_preparar
    from castor import cli as mod_cli

    def executar_roteiro(passos, contexto, relatar=print):
        if erro_do_roteiro is not None:
            raise erro_do_roteiro
        from castor import medicao as mod_medicao
        contexto["medicao"] = mod_medicao.interpretar(RESPOSTA_DA_SONDA)
        if url:
            contexto["url_de_login"] = url
        return ["acesso_inicial"]

    monkeypatch.setattr(mod_preparar, "executar", executar_roteiro)
    monkeypatch.setattr(mod_preparar, "montar_roteiro",
                        lambda **k: [])
    monkeypatch.setattr(mod_cli, "_binario_do_tailscale", lambda: "/bin/tailscale")
    monkeypatch.setattr(mod_cli, "_status_da_rede",
                        lambda binario: json.dumps({"Peer": {"a": {
                            "HostName": "computador-auxiliar", "KeyExpiry": expiracao}}}))
    monkeypatch.setattr("builtins.input", lambda *a: "")


def _com_chave(tmp_path):
    privada = tmp_path / "chave"
    privada.write_text("PRIVADA\n", encoding="utf-8")
    (tmp_path / "chave.pub").write_text("ssh-ed25519 AAAA... ana\n",
                                        encoding="utf-8")
    caminho = tmp_path / "castor.json"
    caminho.write_text(json.dumps({"chave": str(privada), "maquinas": {}}),
                       encoding="utf-8")
    return caminho


def test_preparar_sem_chave_declarada_manda_criar_a_chave(tmp_path, capsys):
    caminho = tmp_path / "castor.json"
    caminho.write_text('{"maquinas": {}}', encoding="utf-8")
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 1
    assert "castor chave criar" in capsys.readouterr().err


def test_preparar_cadastra_a_maquina_e_avisa_o_que_falta(tmp_path, capsys,
                                                         monkeypatch):
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch, expiracao=None)
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 0
    gravado = json.loads(caminho.read_text(encoding="utf-8"))["maquinas"]["computador-auxiliar"]
    assert gravado["papel"] == "cliente"
    assert gravado["usuario"] == "castor"
    assert gravado["endereco"] == "computador-auxiliar.exemplo.test"
    assert "segredos enviar" in capsys.readouterr().out


def test_preparar_mostra_a_url_de_login_capturada(tmp_path, capsys, monkeypatch):
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch, url="https://login.tailscale.com/a/9z8y")
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 0
    assert "9z8y" in capsys.readouterr().out


def test_expiracao_ainda_ativa_nao_anuncia_sucesso_nem_cadastra(tmp_path, capsys,
                                                                monkeypatch):
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch, expiracao="2026-12-16T13:48:07Z")
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 6
    erro = capsys.readouterr().err
    assert "2026-12-16" in erro
    assert json.loads(caminho.read_text(encoding="utf-8"))["maquinas"] == {}


def test_preparar_relata_o_fuso_da_maquina_quando_difere(tmp_path, capsys,
                                                         monkeypatch):
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch)
    monkeypatch.setattr("time.strftime", lambda formato: "+0000")
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 0
    assert "-0400" in capsys.readouterr().out


def test_roteiro_que_para_devolve_codigo_de_preparo(tmp_path, capsys, monkeypatch):
    from castor.preparar import EfeitoNaoConfirmado
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch,
                        erro_do_roteiro=EfeitoNaoConfirmado("o sudo não pegou"))
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 7
    assert "o sudo não pegou" in capsys.readouterr().err


def test_preparar_repassa_a_chave_inicial_ao_roteiro(tmp_path, monkeypatch):
    """Em nuvem não há senha — o primeiro acesso usa a chave que a imagem trouxe."""
    from castor import preparar as mod_preparar
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch)
    recebido = {}
    monkeypatch.setattr(mod_preparar, "montar_roteiro",
                        lambda **k: recebido.update(k) or [])

    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu",
                      "--chave-inicial", "/tmp/chave-da-nuvem"]) == 0
    assert recebido["chave_inicial"] == "/tmp/chave-da-nuvem"


def test_sem_chave_inicial_o_roteiro_nao_recebe_nenhuma(tmp_path, monkeypatch):
    from castor import preparar as mod_preparar
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch)
    recebido = {}
    monkeypatch.setattr(mod_preparar, "montar_roteiro",
                        lambda **k: recebido.update(k) or [])

    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 0
    assert recebido["chave_inicial"] is None


def test_preparar_entrega_o_aviso_quando_o_servico_existe(tmp_path, monkeypatch,
                                                          capsys):
    """Sem o arquivo de aviso, a rotina roda, falha, e ninguém fica sabendo."""
    caminho = _com_chave(tmp_path)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    cofre = tmp_path / "cofre"
    cofre.write_text("SMTP_SENHA=abacaxi-de-mentira\n", encoding="utf-8")
    cofre.chmod(0o600)
    dados["cofre"] = str(cofre)
    dados["maquinas"] = {"computador-principal": {"papel": "principal", "usuario": "ana",
                                     "casa": str(tmp_path), "sistema": "linux"}}
    dados["servicos"] = {"correio": {
        "chaves": ["SMTP_SENHA"], "destino": "$HOME/.config/castor/correio.env"}}
    caminho.write_text(json.dumps(dados), encoding="utf-8")

    _preparo_de_mentira(monkeypatch)
    entregues = []
    monkeypatch.setattr("castor.cli._gravar_na_cliente",
                        lambda destino, arquivo, conteudo:
                        entregues.append(arquivo))

    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 0
    assert any("correio.env" in a for a in entregues)
    assert any("castor.json" in a for a in entregues)
    assert "não sabe avisar" not in capsys.readouterr().out


def test_preparar_sem_servico_de_aviso_avisa_em_voz_alta(tmp_path, monkeypatch,
                                                         capsys):
    caminho = _com_chave(tmp_path)
    _preparo_de_mentira(monkeypatch)
    assert principal(["--cadastro", str(caminho), "maquina", "preparar",
                      "computador-auxiliar", "--endereco", "computador-auxiliar.exemplo.test",
                      "--usuario-inicial", "ubuntu"]) == 0
    saida = capsys.readouterr().out
    assert "não sabe avisar" in saida
    assert "correio" in saida
