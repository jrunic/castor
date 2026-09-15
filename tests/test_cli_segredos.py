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
            "computador-principal": {"papel": "principal", "usuario": "ana",
                        "casa": str(tmp_path), "sistema": "linux"},
            "computador-auxiliar": {"papel": "cliente", "usuario": "castor",
                        "casa": "/home/castor", "sistema": "linux",
                        "endereco": "computador-auxiliar.exemplo.test"},
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
    assert principal(["--cadastro", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "computador-principal",
                      "--destino", str(destino)]) == 0
    assert destino.stat().st_mode & 0o077 == 0
    assert SENHA_SINTETICA in destino.read_text(encoding="utf-8")
    assert SENHA_SINTETICA not in capsys.readouterr().out


def test_gerar_sem_destino_recusa_em_vez_de_imprimir(bancada, capsys):
    """O material nunca ensina a imprimir segredo no terminal."""
    assert principal(["--cadastro", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "computador-principal"]) == 1
    saida = capsys.readouterr()
    assert SENHA_SINTETICA not in saida.out
    assert "--destino" in saida.err


def test_chave_que_falta_no_cofre_nomeia_a_chave(bancada, tmp_path, capsys):
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    dados["servicos"]["correio"]["chaves"].append("TOKEN_AUSENTE")
    bancada.write_text(json.dumps(dados), encoding="utf-8")
    assert principal(["--cadastro", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "computador-principal",
                      "--destino", str(tmp_path / "x.env")]) == 1
    assert "TOKEN_AUSENTE" in capsys.readouterr().err


def test_cofre_frouxo_recusa_e_nao_grava(bancada, tmp_path, capsys):
    (tmp_path / "cofre").chmod(0o644)
    destino = tmp_path / "correio.env"
    assert principal(["--cadastro", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "computador-principal",
                      "--destino", str(destino)]) == 1
    assert not destino.exists()
    assert "chmod 600" in capsys.readouterr().err


def test_manifesto_sem_cofre_declarado_diz_o_que_acrescentar(bancada, tmp_path,
                                                             capsys):
    dados = json.loads(bancada.read_text(encoding="utf-8"))
    del dados["cofre"]
    bancada.write_text(json.dumps(dados), encoding="utf-8")
    assert principal(["--cadastro", str(bancada), "segredos", "gerar",
                      "correio", "--maquina", "computador-principal",
                      "--destino", str(tmp_path / "x.env")]) == 1
    assert "'cofre'" in capsys.readouterr().err


def test_o_cadastro_padrao_e_o_da_configuracao_do_usuario(monkeypatch):
    """O cron da cliente não tem diretório de trabalho que alguém controle."""
    monkeypatch.delenv("CASTOR_CADASTRO", raising=False)
    from castor.cadastro import resolver
    caminho = resolver()
    assert caminho.parent.name == "castor"
    assert caminho.name in ("cadastro.json", "castor.json")


def test_a_variavel_de_ambiente_continua_mandando(monkeypatch):
    monkeypatch.setenv("CASTOR_CADASTRO", "/outro/lugar.json")
    from pathlib import Path
    from castor.cadastro import resolver
    assert resolver() == Path("/outro/lugar.json")


from castor import conexao  # noqa: E402


class EnvioDeMentira:
    def __init__(self, codigo=0):
        self.codigo = codigo
        self.gravacoes = []

    def __call__(self, destino, comando, **opcoes):
        self.gravacoes.append((comando, opcoes.get("entrada")))
        return conexao.Saida(codigo=self.codigo, texto="",
                             erro="Permission denied" if self.codigo else "")


def test_enviar_grava_o_arquivo_do_servico_na_cliente(bancada, monkeypatch):
    envio = EnvioDeMentira()
    monkeypatch.setattr(conexao, "executar", envio)
    assert principal(["--cadastro", str(bancada), "segredos", "enviar",
                      "correio", "--maquina", "computador-auxiliar"]) == 0
    comandos = [c for c, _ in envio.gravacoes]
    assert any("/home/castor/.config/castor/correio.env" in c for c in comandos)
    assert any(e and SENHA_SINTETICA in e for _, e in envio.gravacoes)


def test_enviar_leva_junto_o_manifesto_da_cliente(bancada, monkeypatch):
    envio = EnvioDeMentira()
    monkeypatch.setattr(conexao, "executar", envio)
    principal(["--cadastro", str(bancada), "segredos", "enviar", "correio",
               "--maquina", "computador-auxiliar"])
    comandos = [c for c, _ in envio.gravacoes]
    assert any("/home/castor/.config/castor/castor.json" in c for c in comandos)


def test_o_cofre_nunca_atravessa(bancada, monkeypatch):
    envio = EnvioDeMentira()
    monkeypatch.setattr(conexao, "executar", envio)
    principal(["--cadastro", str(bancada), "segredos", "enviar", "correio",
               "--maquina", "computador-auxiliar"])
    for comando, entrada in envio.gravacoes:
        assert "cofre" not in comando
        if entrada and entrada.lstrip().startswith("{"):
            assert "cofre" not in entrada


def test_enviar_para_a_principal_e_recusado(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", EnvioDeMentira())
    assert principal(["--cadastro", str(bancada), "segredos", "enviar",
                      "correio", "--maquina", "computador-principal"]) == 1
    assert "principal" in capsys.readouterr().err


def test_segredo_nao_aparece_na_saida_do_enviar(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", EnvioDeMentira())
    principal(["--cadastro", str(bancada), "segredos", "enviar", "correio",
               "--maquina", "computador-auxiliar"])
    saida = capsys.readouterr()
    assert SENHA_SINTETICA not in saida.out + saida.err


def test_gravacao_que_falha_devolve_codigo_e_nomeia_o_arquivo(bancada,
                                                              monkeypatch,
                                                              capsys):
    monkeypatch.setattr(conexao, "executar", EnvioDeMentira(codigo=1))
    assert principal(["--cadastro", str(bancada), "segredos", "enviar",
                      "correio", "--maquina", "computador-auxiliar"]) == 5
    erro = capsys.readouterr().err
    assert "correio.env" in erro
    assert SENHA_SINTETICA not in erro


def respondendo(soma_remota):
    def executar(destino, comando, **opcoes):
        if "sha256sum" in comando:
            return conexao.Saida(codigo=0, texto=f"{soma_remota}  arquivo\n",
                                 erro="")
        return conexao.Saida(codigo=0, texto="", erro="")
    return executar


def soma_esperada(manifesto):
    from castor import segredos as mod_segredos
    from castor.manifesto import ler
    lido = ler(manifesto)
    return mod_segredos.soma(mod_segredos.montar(
        lido, "correio", "computador-auxiliar",
        {"SMTP_SERVIDOR": "smtp.exemplo.test", "SMTP_SENHA": SENHA_SINTETICA}))


def test_estado_em_dia_quando_a_soma_bate(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", respondendo(soma_esperada(bancada)))
    assert principal(["--cadastro", str(bancada), "segredos", "estado"]) == 0
    assert "em dia" in capsys.readouterr().out


def test_estado_desatualizado_devolve_codigo_proprio(bancada, monkeypatch,
                                                     capsys):
    monkeypatch.setattr(conexao, "executar", respondendo("0" * 64))
    assert principal(["--cadastro", str(bancada), "segredos", "estado"]) == 8
    assert "desatualizado" in capsys.readouterr().out


def test_arquivo_ausente_na_cliente_e_reportado_como_ausente(bancada,
                                                             monkeypatch,
                                                             capsys):
    monkeypatch.setattr(conexao, "executar", respondendo(""))
    assert principal(["--cadastro", str(bancada), "segredos", "estado"]) == 8
    assert "ausente" in capsys.readouterr().out


def test_estado_nao_imprime_valor_nenhum(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", respondendo("0" * 64))
    principal(["--cadastro", str(bancada), "segredos", "estado"])
    saida = capsys.readouterr()
    assert SENHA_SINTETICA not in saida.out + saida.err


def test_maquina_inalcancavel_nao_derruba_o_relatorio_inteiro(bancada,
                                                              monkeypatch,
                                                              capsys):
    """Uma máquina fora do ar não pode esconder o estado das outras."""
    def cair(destino, comando, **opcoes):
        return conexao.Saida(codigo=255, texto="",
                             erro="ssh: Could not resolve hostname computador-auxiliar")
    monkeypatch.setattr(conexao, "executar", cair)
    assert principal(["--cadastro", str(bancada), "segredos", "estado"]) == 8
    assert "inalcançável" in capsys.readouterr().out


def test_a_principal_nao_entra_no_relatorio(bancada, monkeypatch, capsys):
    monkeypatch.setattr(conexao, "executar", respondendo(soma_esperada(bancada)))
    principal(["--cadastro", str(bancada), "segredos", "estado"])
    assert "computador-principal" not in capsys.readouterr().out
