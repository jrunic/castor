import json

import pytest

from castor import conexao
from castor.cli import principal


@pytest.fixture
def bancada(tmp_path):
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "chave": str(tmp_path / "chave"),
        "maquinas": {
            "computador-principal": {"papel": "principal", "usuario": "ana",
                        "casa": str(tmp_path), "sistema": "darwin"},
            "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "computador-auxiliar.exemplo.test"},
        },
        "atualizacao": {"alvos": {
            "castor": {"tipo": "castor", "maquinas": ["computador-auxiliar"]},
            "jd-exemplo": {"tipo": "pipx", "pacote": "jd-exemplo",
                           "maquinas": ["computador-auxiliar"],
                           "versao": "jd-exemplo --version"},
        }},
    }), encoding="utf-8")
    return manifesto


class MaquinaDeMentira:
    """Responde por CONTEÚDO do comando, não por ordem de chamada.

    Fila global acopla o teste à ordem em que a implementação pergunta as
    coisas: qualquer reordenação passa a responder a versão errada para a
    pergunta errada, e o vermelho que sai disso é ilegível.
    """

    def __init__(self, respostas=None):
        self.respostas = {gatilho: iter(valores)
                          for gatilho, valores in (respostas or {}).items()}
        self.comandos = []

    def __call__(self, destino, comando, **opcoes):
        self.comandos.append(comando)
        for gatilho, valores in self.respostas.items():
            if gatilho in comando:
                return conexao.Saida(codigo=0, texto=next(valores, ""), erro="")
        return conexao.Saida(codigo=0, texto="", erro="")


def versoes(pipx=("1.0", "1.1"), castor=("0.1.1", "0.1.2")):
    return MaquinaDeMentira({"jd-exemplo --version": pipx,
                             "castor --versao": castor})


def test_rodar_pergunta_a_versao_antes_e_depois(bancada, monkeypatch, capsys):
    maquina = versoes()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar"]) == 0
    assert "1.0 → 1.1" in capsys.readouterr().out


def test_o_castor_e_o_ultimo_alvo(bancada, monkeypatch):
    """Castor novo quebrado não pode derrubar a rodada que já estava andando."""
    maquina = versoes()
    monkeypatch.setattr(conexao, "executar", maquina)
    principal(["--manifesto", str(bancada), "atualizacao", "rodar"])
    ordem = " | ".join(maquina.comandos)
    assert ordem.index("pipx upgrade") < ordem.index("instalar.sh")


def test_a_principal_se_atualiza_localmente_e_sem_ssh(bancada, monkeypatch,
                                                      capsys):
    """O _destino_de recusa a principal, e com razão: não há ssh de volta.

    É esta a metade macOS do critério 15. Sem ela, a rodada morre no meio com
    erro de manifesto na primeira máquina que for a principal.
    """
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["atualizacao"]["alvos"]["castor"]["maquinas"] = ["computador-principal", "computador-auxiliar"]
    bancada.write_text(json.dumps(dados), encoding="utf-8")

    maquina = versoes()
    monkeypatch.setattr(conexao, "executar", maquina)
    locais = []

    def aqui(comando):
        locais.append(comando)
        return "0.1.1", ""   # (saída, erro) — quem falha explica no erro
    monkeypatch.setattr("castor.cli._aqui", aqui)

    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar"]) == 0
    assert any("instalar.sh" in c for c in locais), locais
    assert "computador-principal" in capsys.readouterr().out


def test_alvo_que_nao_responde_depois_sai_onze(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", MaquinaDeMentira())
    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar"]) == 11
    assert "não respondeu" in capsys.readouterr().out


def test_versao_igual_nao_e_falha(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar",
                        versoes(pipx=("1.0", "1.0"), castor=("0.1.1", "0.1.1")))
    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar"]) == 0
    assert "sem mudança" in capsys.readouterr().out


def test_maquina_fora_do_ar_nao_interrompe_as_outras(bancada, monkeypatch,
                                                     capsys):
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["maquinas"]["moinho"] = {"papel": "cliente", "usuario": "castor",
                                   "casa": "/home/castor", "sistema": "linux",
                                   "endereco": "moinho.exemplo.test"}
    dados["atualizacao"]["alvos"]["jd-exemplo"]["maquinas"] = ["moinho",
                                                               "computador-auxiliar"]
    bancada.write_text(json.dumps(dados), encoding="utf-8")

    def as_vezes_cai(destino, comando, **opcoes):
        if destino.endereco.startswith("moinho"):
            return conexao.Saida(codigo=255, texto="",
                                 erro="ssh: Could not resolve hostname moinho")
        if "--version" in comando or "--versao" in comando:
            return conexao.Saida(codigo=0, texto="1.1", erro="")
        return conexao.Saida(codigo=0, texto="", erro="")
    monkeypatch.setattr(conexao, "executar", as_vezes_cai)

    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar"]) == 11
    saida = capsys.readouterr().out
    assert "inalcançável" in saida
    assert "computador-auxiliar" in saida  # a outra máquina saiu no relatório


def test_seco_mostra_o_que_faria_e_nao_faz(bancada, monkeypatch, capsys):
    maquina = versoes()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar",
                      "--ensaio"]) == 0
    assert not any("pipx upgrade" in c for c in maquina.comandos)
    saida = capsys.readouterr().out
    assert "[ensaio]" in saida and "pipx upgrade" in saida


def test_alvo_com_reiniciar_chama_o_servico(bancada, monkeypatch):
    """Atualizar o pacote e deixar o serviço com o binário velho é meio trabalho."""
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["atualizacao"]["alvos"]["jd-exemplo"]["reiniciar"] = "sentinela"
    bancada.write_text(json.dumps(dados), encoding="utf-8")

    maquina = MaquinaDeMentira({"jd-exemplo --version": ("1.0", "1.1"),
                                "castor --versao": ("0.1.1", "0.1.2"),
                                "is-active": ("active", "active")})
    monkeypatch.setattr(conexao, "executar", maquina)
    principal(["--manifesto", str(bancada), "atualizacao", "rodar"])
    assert any("restart sentinela.service" in c for c in maquina.comandos)


def test_estado_diz_que_versao_esta_em_cada_maquina(bancada, monkeypatch,
                                                    capsys):
    maquina = versoes()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--manifesto", str(bancada), "atualizacao",
                      "estado"]) == 0
    saida = capsys.readouterr().out
    assert "jd-exemplo" in saida and "1.0" in saida


def test_estado_nao_atualiza_nada(bancada, monkeypatch):
    maquina = versoes()
    monkeypatch.setattr(conexao, "executar", maquina)
    principal(["--manifesto", str(bancada), "atualizacao", "estado"])
    assert not any("upgrade" in c or "instalar.sh" in c
                   for c in maquina.comandos)


def test_estado_com_alvo_que_nao_responde_sai_onze(bancada, monkeypatch,
                                                   capsys):
    monkeypatch.setattr(conexao, "executar", MaquinaDeMentira())
    assert principal(["--manifesto", str(bancada), "atualizacao",
                      "estado"]) == 11
    assert "ausente" in capsys.readouterr().out


def test_alvo_que_falha_diz_o_que_a_maquina_respondeu(bancada, monkeypatch,
                                                      capsys):
    """'não respondeu' sem a razão manda quem lê procurar no escuro.

    O instalador explica a causa no erro padrão — se o comando descarta isso,
    quem opera vê só o sintoma.
    """
    def recusa(destino, comando, **opcoes):
        if "instalar.sh" in comando or "upgrade" in comando:
            return conexao.Saida(
                codigo=1, texto="",
                erro="o python desta máquina é 3.9.6; o castor precisa de 3.12")
        return conexao.Saida(codigo=0, texto="", erro="")
    monkeypatch.setattr(conexao, "executar", recusa)
    assert principal(["--manifesto", str(bancada), "atualizacao", "rodar"]) == 11
    saida = capsys.readouterr().out
    assert "3.12" in saida, saida
