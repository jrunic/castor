import io
import json
from pathlib import Path

import castor
import pytest

from castor import configurar
from castor.cli import principal
from castor.rede import ErroDeRede


def test_perguntar_aceita_o_default_do_enter(monkeypatch, capsys):
    monkeypatch.setattr("castor.configurar.entrada", io.StringIO("\n"))
    resposta = configurar._perguntar("aviso? ", validar=lambda r: r,
                                     default="n", esperado="s ou n")
    assert resposta == "n"
    assert "[Enter = n]" in capsys.readouterr().out


def test_perguntar_repergunta_nomeando_o_que_esperava(monkeypatch, capsys):
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("lixo\nlixo\ns\n"))
    resposta = configurar._perguntar(
        "aviso? ", validar=lambda r: r if r in ("s", "n") else None,
        esperado="s ou n")
    assert resposta == "s"
    assert capsys.readouterr().out.count("esperava: s ou n") == 2


def test_perguntar_para_apos_tres_erros_sem_resposta(monkeypatch):
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("a\nb\nc\n"))
    with pytest.raises(configurar.EsgotouPergunta) as erro:
        configurar._perguntar("porta: ", validar=lambda r: None,
                              esperado="um número")
    assert "porta" in str(erro.value)


def test_configurar_abre_com_cabecalho(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\n\n"))
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    assert principal(["configurar"]) == 0
    saida = capsys.readouterr().out
    assert f"Castor by Orlando Ferreira v{castor.__version__}" in saida
    assert "nada é gravado" in saida
    assert "Ctrl+C" in saida


def test_configurar_grava_depois_da_rede_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\n\n"))
    ordem = []
    monkeypatch.setattr("castor.configurar.garantir_rede",
                        lambda **_: ordem.append("rede"))
    assert principal(["configurar"]) == 0
    assert ordem == ["rede"]
    dados = json.loads((tmp_path / "cadastro.json").read_text(encoding="utf-8"))
    assert dados["chave"]
    assert dados["maquinas"]["computador-principal"]["papel"] == "principal"
    assert "aviso" not in dados
    assert not (tmp_path / ".config" / "castor" / "cofre").exists()
    saida = capsys.readouterr()
    assert "principal configurada" in saida.out
    assert "cadastro.json" in saida.out


def test_previa_vem_antes_da_rede(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    ordem = []
    monkeypatch.setattr("castor.configurar.garantir_rede",
                        lambda **_: ordem.append("rede"))
    real_previa = configurar.previa

    def previa_marcada(plano):
        ordem.append("previa")
        return real_previa(plano)

    monkeypatch.setattr("castor.configurar.previa", previa_marcada)
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\n\n"))
    assert principal(["configurar"]) == 0
    assert ordem == ["previa", "rede"]


def test_cancelar_na_previa_nao_faz_nada(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    chamou = []
    monkeypatch.setattr("castor.configurar.garantir_rede",
                        lambda **_: chamou.append("rede"))
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\nn\n"))
    assert principal(["configurar"]) == 1
    assert chamou == []
    assert not (tmp_path / "cadastro.json").exists()
    assert not (tmp_path / ".ssh" / "castor").exists()
    assert "nada foi feito" in capsys.readouterr().out


def test_previa_diz_que_instala_quando_a_sonda_nao_acha_binario(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    monkeypatch.setattr("castor.configurar._sonda_padrao", lambda: None)
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\n\n"))
    assert principal(["configurar"]) == 0
    assert "instalar o Tailscale" in capsys.readouterr().out


def test_previa_nao_diz_que_instala_quando_a_sonda_acha_binario(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    monkeypatch.setattr("castor.configurar._sonda_padrao",
                        lambda: "/x/tailscale")
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\n\n"))
    assert principal(["configurar"]) == 0
    assert "instalar o Tailscale" not in capsys.readouterr().out


def test_rede_falhando_depois_da_confirmacao_nada_cria(tmp_path, monkeypatch,
                                                       capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.entrada",
                        io.StringIO("c\ncomputador-principal\nn\n\n"))

    def garantir(**_):
        raise ErroDeRede("preciso de sudo uma vez.")

    monkeypatch.setattr("castor.configurar.garantir_rede", garantir)
    assert principal(["configurar"]) == 1
    assert not (tmp_path / "cadastro.json").exists()
    assert not (tmp_path / ".ssh" / "castor").exists()
    assert not (tmp_path / ".config" / "castor" / "cofre").exists()
    erro = capsys.readouterr().err
    assert "sudo" in erro
    assert "não terminou" in erro


def test_configurar_com_entrada_fechada_sai_limpo(tmp_path, monkeypatch,
                                                  capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.entrada", io.StringIO(""))
    assert principal(["configurar"]) == 1
    saida = capsys.readouterr()
    assert "Traceback" not in saida.out + saida.err
    assert not (tmp_path / "cadastro.json").exists()


def test_configurar_google_grava_cofre_e_nao_imprime_senha(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "castor.configurar.entrada",
        io.StringIO(
            "c\ncomputador-principal\ns\ng\nana@gmail.com\nsenha-secreta\n\n"),
    )
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    assert principal(["configurar"]) == 0
    saida = capsys.readouterr()
    assert "senha-secreta" not in saida.out + saida.err
    cofre = tmp_path / ".config" / "castor" / "cofre"
    assert cofre.exists()
    assert oct(cofre.stat().st_mode)[-3:] == "600"
    texto = cofre.read_text(encoding="utf-8")
    assert "SMTP_SENHA=senha-secreta" in texto
    dados = json.loads((tmp_path / "cadastro.json").read_text(encoding="utf-8"))
    assert dados["aviso"]["servidor"] == "smtp.gmail.com"
    assert dados["aviso"]["porta"] == 587
    assert dados["servicos"]["correio"]["chaves"][0] == "SMTP_SERVIDOR"


def test_configurar_outro_smtp_pergunta_servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "castor.configurar.entrada",
        io.StringIO(
            "c\ncomputador-principal\ns\no\nsmtp.exemplo.test\n587\n"
            "ana@exemplo.test\nsegredo\n\n\n\n"
        ),
    )
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    assert principal(["configurar"]) == 0
    dados = json.loads((tmp_path / "cadastro.json").read_text(encoding="utf-8"))
    assert dados["aviso"]["servidor"] == "smtp.exemplo.test"


def test_porta_nao_inteira_repergunta_sem_traceback(tmp_path, monkeypatch,
                                                    capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "castor.configurar.entrada",
        io.StringIO("c\ncomputador-principal\ns\no\nsmtp.exemplo.test\n"
                    "abcd\n587\nana@exemplo.test\nsegredo\n\n\n\n"),
    )
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    assert principal(["configurar"]) == 0
    saida = capsys.readouterr()
    assert "Traceback" not in saida.out + saida.err
    assert "esperava" in saida.out
