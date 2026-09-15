import json

import pytest

from castor import conexao
from castor.cli import principal

STATUS_SEM_EXPIRACAO = json.dumps(
    {"Peer": {"a": {"HostName": "computador-auxiliar", "KeyExpiry": None}}})
STATUS_COM_EXPIRACAO = json.dumps(
    {"Peer": {"a": {"HostName": "computador-auxiliar", "KeyExpiry": "2026-12-16T13:48:07Z"}}})


@pytest.fixture
def bancada(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTOR_ESTADO", str(tmp_path / "estado"))
    cofre = tmp_path / "cofre"
    cofre.write_text("SMTP_SENHA=abacaxi-de-mentira\n", encoding="utf-8")
    cofre.chmod(0o600)
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "cofre": str(cofre),
        "chave": str(tmp_path / "chave"),
        "maquinas": {
            "computador-principal": {"papel": "principal", "usuario": "ana",
                        "casa": str(tmp_path), "sistema": "darwin"},
            "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "computador-auxiliar.exemplo.test"},
        },
        "aviso": {"servidor": "smtp.exemplo.test", "porta": 587,
                  "usuario": "castor@exemplo.test", "de": "de@exemplo.test",
                  "para": "para@exemplo.test", "janela_em_minutos": 60,
                  "variavel": "SMTP_SENHA"},
        "ronda": {"checagens": {
            "disco": {"tipo": "comando", "maquina": "computador-auxiliar",
                      "comando": "test 1 -lt 2"},
            "sentinela": {"tipo": "servico", "maquina": "computador-auxiliar",
                          "servico": "sentinela"},
            "nao-expira": {"tipo": "expiracao", "maquina": "computador-auxiliar"},
        }},
    }), encoding="utf-8")
    return manifesto


class MaquinaDeMentira:
    def __init__(self, respostas=None, codigo=0):
        self.respostas = respostas or {}
        self.codigo = codigo
        self.comandos = []

    def __call__(self, destino, comando, **opcoes):
        self.comandos.append(comando)
        for gatilho, resposta in self.respostas.items():
            if gatilho in comando:
                return conexao.Saida(codigo=0, texto=resposta, erro="")
        return conexao.Saida(codigo=self.codigo, texto="", erro="")


class CorreioDeMentira:
    """Fronteira de sistema: o SMTP. O resto do caminho roda de verdade."""

    enviadas = []

    def __init__(self, **kwargs):
        self.configuracao = kwargs

    def enviar(self, mensagem):
        CorreioDeMentira.enviadas.append(mensagem)


@pytest.fixture(autouse=True)
def correio_limpo(monkeypatch):
    CorreioDeMentira.enviadas = []
    monkeypatch.setattr("castor.correio.RemetenteSMTP", CorreioDeMentira)
    return CorreioDeMentira


def com_rede(monkeypatch, status=STATUS_SEM_EXPIRACAO):
    monkeypatch.setattr("castor.cli._binario_do_tailscale", lambda: "/bin/ts")
    monkeypatch.setattr("castor.cli._status_da_rede", lambda binario: status)


def tudo_bem(monkeypatch):
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "active\n"}))
    com_rede(monkeypatch)


def tudo_mal(monkeypatch):
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "failed\n"}, codigo=1))
    com_rede(monkeypatch)


def so_o_servico_mal(monkeypatch):
    """Uma checagem falhando, e só uma — o comando continua saindo zero.

    É um aviso por checagem que piorou, então medir 'um e-mail' exige uma
    falha só.
    """
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "failed\n"}, codigo=0))
    com_rede(monkeypatch)


def test_ronda_que_passa_em_tudo_sai_zero(bancada, monkeypatch, capsys):
    tudo_bem(monkeypatch)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar"]) == 0
    saida = capsys.readouterr().out
    assert "disco" in saida and "passou" in saida


def test_a_expiracao_e_conferida_na_principal_e_nao_na_cliente(bancada,
                                                               monkeypatch):
    """Emenda ao critério 14: um nó não lê a própria expiração."""
    maquina = MaquinaDeMentira({"is-active": "active\n"})
    monkeypatch.setattr(conexao, "executar", maquina)
    com_rede(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    assert not any("tailscale" in c for c in maquina.comandos)


def test_expiracao_ativa_e_falha_com_a_data(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar",
                        MaquinaDeMentira({"is-active": "active\n"}))
    com_rede(monkeypatch, STATUS_COM_EXPIRACAO)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar"]) == 10
    assert "2026-12-16" in capsys.readouterr().out


def test_checagem_que_falha_sai_dez(bancada, monkeypatch, capsys):
    tudo_mal(monkeypatch)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar"]) == 10
    assert "falhou" in capsys.readouterr().out


def test_maquina_inalcancavel_vira_uma_falha_so(bancada, monkeypatch, capsys):
    def cair(destino, comando, **opcoes):
        return conexao.Saida(codigo=255, texto="",
                             erro="ssh: Could not resolve hostname computador-auxiliar")
    monkeypatch.setattr(conexao, "executar", cair)
    com_rede(monkeypatch)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar"]) == 10

    linhas = [l for l in capsys.readouterr().out.splitlines() if "\t" in l]
    nomes = [l.split("\t")[0] for l in linhas]
    assert nomes.count("maquina:computador-auxiliar") == 1
    assert "disco" not in nomes and "sentinela" not in nomes
    # A expiração roda AQUI, então a máquina fora do ar não a impede.
    assert "expiracao:computador-auxiliar" in nomes


def test_seco_nao_monta_correio_nenhum(bancada, monkeypatch, capsys):
    """Medido por estado observável, não por mock do que eu mesmo escrevi."""
    tudo_mal(monkeypatch)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar",
                      "--ensaio"]) == 10
    assert "[ensaio]" in capsys.readouterr().out
    assert CorreioDeMentira.enviadas == []


def test_seco_nao_grava_e_por_isso_nao_apaga_a_linha_de_base(bancada,
                                                             monkeypatch,
                                                             tmp_path):
    """Seco que grava resetaria a comparação da ronda seguinte."""
    tudo_bem(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    arquivo = tmp_path / "estado" / "ronda.json"
    antes = arquivo.read_text(encoding="utf-8")

    tudo_mal(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar", "--ensaio"])
    assert arquivo.read_text(encoding="utf-8") == antes


def test_a_ronda_grava_o_resultado(bancada, monkeypatch, tmp_path):
    tudo_bem(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    gravado = json.loads(
        (tmp_path / "estado" / "ronda.json").read_text(encoding="utf-8"))
    assert {r["nome"] for r in gravado["resultados"]} >= {"disco", "sentinela"}


def test_checagem_mal_declarada_para_antes_de_rodar_qualquer_coisa(bancada,
                                                                   monkeypatch,
                                                                   capsys):
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["ronda"]["checagens"]["torta"] = {"maquina": "computador-auxiliar"}
    bancada.write_text(json.dumps(dados), encoding="utf-8")
    maquina = MaquinaDeMentira()
    monkeypatch.setattr(conexao, "executar", maquina)
    com_rede(monkeypatch)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar"]) == 1
    assert maquina.comandos == []
    assert "tipo" in capsys.readouterr().err


def test_checagem_que_piorou_manda_um_email(bancada, monkeypatch):
    """A senha de SMTP sai do cofre da principal — aqui não há arquivo de
    serviço, que é coisa da cliente."""
    so_o_servico_mal(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    assert len(CorreioDeMentira.enviadas) == 1
    assert "ronda" in CorreioDeMentira.enviadas[0]["Subject"]


def test_a_mesma_falha_na_janela_nao_reenvia(bancada, monkeypatch):
    so_o_servico_mal(monkeypatch)
    for _ in range(3):
        principal(["--manifesto", str(bancada), "ronda", "rodar"])
    assert len(CorreioDeMentira.enviadas) == 1


def test_quem_voltou_ao_normal_avisa_tambem(bancada, monkeypatch):
    """Sem isto, quem recebeu o aviso de falha nunca sabe que acabou."""
    so_o_servico_mal(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    tudo_bem(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])

    assuntos = [m["Subject"] for m in CorreioDeMentira.enviadas]
    assert len(assuntos) == 2, assuntos
    assert "voltou" in assuntos[1].lower()


def test_falha_depois_de_voltar_avisa_de_novo_na_mesma_janela(bancada,
                                                              monkeypatch):
    """falhou → avisou → voltou → avisou → falhou de novo, tudo na janela.

    Sem o esquecimento na supressão, a última falha fica muda — e silêncio logo
    depois de um 'voltou ao normal' lê-se como 'continua bem'.
    """
    for preparar_maquina in (so_o_servico_mal, tudo_bem, so_o_servico_mal):
        preparar_maquina(monkeypatch)
        principal(["--manifesto", str(bancada), "ronda", "rodar"])
    assert len(CorreioDeMentira.enviadas) == 3, \
        [m["Subject"] for m in CorreioDeMentira.enviadas]


def test_correio_fora_do_ar_nao_derruba_a_ronda(bancada, monkeypatch, capsys):
    """Mesma lição do plano 4: o aviso que falha não engole o resultado."""
    class Caido(CorreioDeMentira):
        def enviar(self, mensagem):
            raise OSError("nodename nor servname provided")
    monkeypatch.setattr("castor.correio.RemetenteSMTP", Caido)
    tudo_mal(monkeypatch)
    assert principal(["--manifesto", str(bancada), "ronda", "rodar"]) == 10
    assert "aviso não saiu" in capsys.readouterr().err


def test_estado_le_o_arquivo_e_nao_reexecuta(bancada, monkeypatch, capsys):
    """Consulta que executa tem efeito colateral, e aí dá medo de perguntar."""
    tudo_bem(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])

    maquina = MaquinaDeMentira()
    monkeypatch.setattr(conexao, "executar", maquina)
    assert principal(["--manifesto", str(bancada), "ronda", "estado"]) == 0
    assert maquina.comandos == []
    assert "disco" in capsys.readouterr().out


def test_estado_diz_quando_foi_a_ultima(bancada, monkeypatch, capsys):
    """Resultado velho sem data é pior que nenhum resultado."""
    tudo_bem(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    principal(["--manifesto", str(bancada), "ronda", "estado"])
    assert "última ronda" in capsys.readouterr().out.lower()


def test_estado_sem_ronda_nenhuma_diz_o_que_fazer(bancada, capsys):
    assert principal(["--manifesto", str(bancada), "ronda", "estado"]) == 1
    assert "castor ronda rodar" in capsys.readouterr().err


def test_estado_com_falha_guardada_sai_dez(bancada, monkeypatch):
    tudo_mal(monkeypatch)
    principal(["--manifesto", str(bancada), "ronda", "rodar"])
    assert principal(["--manifesto", str(bancada), "ronda", "estado"]) == 10
