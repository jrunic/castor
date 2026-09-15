import json

import pytest

from castor import conexao
from castor.cli import principal

SENHA_SINTETICA = "abacaxi-de-mentira-123"


@pytest.fixture
def bancada(tmp_path):
    cofre = tmp_path / "cofre"
    cofre.write_text(f"TOKEN_DA_SENTINELA={SENHA_SINTETICA}\n", encoding="utf-8")
    cofre.chmod(0o600)
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "cofre": str(cofre),
        "chave": str(tmp_path / "chave"),
        "maquinas": {
            "computador-principal": {"papel": "principal", "usuario": "ana",
                        "casa": str(tmp_path), "sistema": "linux"},
            "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "computador-auxiliar.exemplo.test"},
            "praia": {"papel": "cliente", "usuario": "castor",
                      "casa": "/Users/castor", "sistema": "darwin",
                      "endereco": "praia.exemplo.test"},
        },
        "servicos": {
            "sentinela": {
                "chaves": ["TOKEN_DA_SENTINELA"],
                "destino": "$HOME/.config/castor/sentinela.env",
                "comando": "$HOME/.local/bin/sentinela --vigiar",
                "descricao": "Sentinela do computador-auxiliar",
                "maquinas": ["computador-auxiliar"]},
            "correio": {"chaves": ["TOKEN_DA_SENTINELA"],
                        "destino": "$HOME/.config/castor/correio.env"},
        },
    }), encoding="utf-8")
    return manifesto


class MaquinaDeMentira:
    """Responde aos comandos como a máquina responderia, e guarda a ordem."""

    def __init__(self, respostas=None):
        self.respostas = respostas or {}
        self.comandos = []

    def __call__(self, destino, comando, **opcoes):
        self.comandos.append(comando)
        for gatilho, resposta in self.respostas.items():
            if gatilho in comando:
                return conexao.Saida(codigo=0, texto=resposta, erro="")
        return conexao.Saida(codigo=0, texto="", erro="")


def de_pe():
    return MaquinaDeMentira({"is-active": "active\n", "show-user": "Linger=yes\n",
                             "is-enabled": "enabled\n"})


def test_instalar_entrega_o_segredo_antes_de_subir(bancada, monkeypatch):
    """Sem o arquivo de ambiente, o systemd recusa a unit longe da causa."""
    maquina = de_pe()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "instalar",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 0
    entrega = next(i for i, c in enumerate(maquina.comandos)
                   if "sentinela.env" in c)
    subida = next(i for i, c in enumerate(maquina.comandos)
                  if "enable --now" in c)
    assert entrega < subida


def test_instalar_grava_a_unit_e_recarrega_antes_de_ligar(bancada, monkeypatch):
    maquina = de_pe()
    monkeypatch.setattr(conexao, "executar", maquina)
    principal(["--cadastro", str(bancada), "servico", "instalar", "sentinela",
               "--maquina", "computador-auxiliar"])
    ordem = " | ".join(maquina.comandos)
    assert "/home/castor/.config/systemd/user/sentinela.service" in ordem
    assert ordem.index("daemon-reload") < ordem.index("enable --now")


def test_instalar_liga_o_linger_e_confere(bancada, monkeypatch):
    """Sem linger, o serviço morre quando a última sessão fecha."""
    maquina = de_pe()
    monkeypatch.setattr(conexao, "executar", maquina)
    principal(["--cadastro", str(bancada), "servico", "instalar", "sentinela",
               "--maquina", "computador-auxiliar"])
    ordem = " | ".join(maquina.comandos)
    assert "enable-linger" in ordem
    assert "show-user" in ordem


def test_linger_que_nao_pegou_para_a_instalacao(bancada, monkeypatch, capsys):
    maquina = MaquinaDeMentira({"is-active": "active\n",
                                "show-user": "Linger=no\n"})
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "instalar",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 9
    assert "linger" in capsys.readouterr().err


def test_servico_que_nao_fica_ativo_devolve_nove(bancada, monkeypatch, capsys):
    maquina = MaquinaDeMentira({"is-active": "failed\n",
                                "show-user": "Linger=yes\n"})
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "instalar",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 9
    erro = capsys.readouterr().err
    assert "failed" in erro
    assert "castor servico registro" in erro


def test_servico_sem_comando_recusa_nomeando_o_manifesto(bancada, monkeypatch,
                                                         capsys):
    monkeypatch.setattr(conexao, "executar", de_pe())
    assert principal(["--cadastro", str(bancada), "servico", "instalar",
                      "correio", "--maquina", "computador-auxiliar"]) == 1
    assert "comando" in capsys.readouterr().err


def test_cliente_macos_e_recusada_com_explicacao(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", de_pe())
    assert principal(["--cadastro", str(bancada), "servico", "instalar",
                      "sentinela", "--maquina", "praia"]) == 1
    assert "Linux" in capsys.readouterr().err


def test_comando_que_muda_o_mundo_e_falha_para_a_instalacao(bancada, monkeypatch,
                                                            capsys):
    """daemon-reload que falha só apareceria no is-active, longe da causa."""
    class Recusa(MaquinaDeMentira):
        def __call__(self, destino, comando, **opcoes):
            self.comandos.append(comando)
            if "daemon-reload" in comando:
                return conexao.Saida(codigo=1, texto="",
                                     erro="Failed to connect to bus")
            if "show-user" in comando:
                return conexao.Saida(codigo=0, texto="Linger=yes\n", erro="")
            return conexao.Saida(codigo=0, texto="", erro="")

    monkeypatch.setattr(conexao, "executar", Recusa())
    assert principal(["--cadastro", str(bancada), "servico", "instalar",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 9
    assert "daemon-reload" in capsys.readouterr().err


def test_o_segredo_nao_aparece_na_saida(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", de_pe())
    principal(["--cadastro", str(bancada), "servico", "instalar", "sentinela",
               "--maquina", "computador-auxiliar"])
    saida = capsys.readouterr()
    assert SENHA_SINTETICA not in saida.out + saida.err


def parado():
    return MaquinaDeMentira({"is-active": "inactive\n",
                             "is-enabled": "disabled\n"})


def test_remover_para_desabilita_e_tira_a_unit(bancada, monkeypatch):
    maquina = parado()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "remover",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 0
    ordem = " | ".join(maquina.comandos)
    assert "disable --now" in ordem
    assert "sentinela.service" in ordem
    assert "daemon-reload" in ordem


def test_remover_tira_tambem_o_segredo_do_servico(bancada, monkeypatch):
    """Credencial esquecida depois de remover o serviço é sujeira perigosa."""
    maquina = parado()
    monkeypatch.setattr(conexao, "executar", maquina)
    principal(["--cadastro", str(bancada), "servico", "remover", "sentinela",
               "--maquina", "computador-auxiliar"])
    assert any("sentinela.env" in c for c in maquina.comandos)


def test_remover_diz_que_o_linger_ficou(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", parado())
    principal(["--cadastro", str(bancada), "servico", "remover", "sentinela",
               "--maquina", "computador-auxiliar"])
    assert "linger" in capsys.readouterr().out


def test_servico_que_nao_parou_devolve_nove(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "active\n"}))
    assert principal(["--cadastro", str(bancada), "servico", "remover",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 9
    assert "continua ativo" in capsys.readouterr().err


def test_servico_que_continua_habilitado_devolve_nove(bancada, monkeypatch,
                                                      capsys):
    """Parar e não desabilitar deixa o serviço voltar no próximo boot."""
    maquina = MaquinaDeMentira({"is-active": "inactive\n",
                                "is-enabled": "enabled\n"})
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "remover",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 9
    assert "habilitado" in capsys.readouterr().err


def test_estado_lista_por_servico_e_maquina(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", de_pe())
    assert principal(["--cadastro", str(bancada), "servico", "estado"]) == 0
    saida = capsys.readouterr().out
    assert "sentinela" in saida and "computador-auxiliar" in saida and "active" in saida


def test_estado_ignora_servico_que_nao_tem_comando(bancada, monkeypatch, capsys):
    """'correio' é só segredo — não é serviço, e não aparece como se fosse."""
    monkeypatch.setattr(conexao, "executar", de_pe())
    principal(["--cadastro", str(bancada), "servico", "estado"])
    assert "correio" not in capsys.readouterr().out


def test_estado_com_servico_caido_devolve_nove(bancada, monkeypatch):
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "failed\n"}))
    assert principal(["--cadastro", str(bancada), "servico", "estado"]) == 9


def test_maquina_que_nao_e_linux_aparece_como_pulada(bancada, monkeypatch,
                                                     capsys):
    """Pular em silêncio faria o relatório parecer completo."""
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["servicos"]["sentinela"]["maquinas"] = ["praia"]
    bancada.write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setattr(conexao, "executar", de_pe())
    principal(["--cadastro", str(bancada), "servico", "estado"])
    saida = capsys.readouterr().out
    assert "pulada" in saida and "darwin" in saida


def test_reiniciar_confere_que_voltou(bancada, monkeypatch, capsys):
    """É por aqui que um segredo trocado chega ao processo que o consome."""
    maquina = de_pe()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "reiniciar",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 0
    ordem = " | ".join(maquina.comandos)
    assert ordem.index("restart") < ordem.index("is-active")
    assert "ativo" in capsys.readouterr().out


def test_reiniciar_que_nao_voltou_devolve_nove(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "failed\n"}))
    assert principal(["--cadastro", str(bancada), "servico", "reiniciar",
                      "sentinela", "--maquina", "computador-auxiliar"]) == 9
    assert "castor servico registro" in capsys.readouterr().err


def test_registro_traz_as_linhas_pedidas(bancada, monkeypatch, capsys):
    maquina = MaquinaDeMentira({"journalctl": "linha um\nlinha dois\n"})
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--cadastro", str(bancada), "servico", "registro",
                      "sentinela", "--maquina", "computador-auxiliar", "--linhas", "5"]) == 0
    assert "linha dois" in capsys.readouterr().out
    assert any("-n 5" in c for c in maquina.comandos)
