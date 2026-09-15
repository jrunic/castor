import io
import json
from pathlib import Path

from castor.cli import principal
from castor.rede import ErroDeRede


def test_configurar_grava_depois_da_rede_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    entrada = io.StringIO("c\ncomputador-principal\nn\n")
    monkeypatch.setattr("castor.configurar.entrada", entrada)

    def garantir(**_):
        return None

    monkeypatch.setattr("castor.configurar.garantir_rede", garantir)
    assert principal(["configurar"]) == 0
    dados = json.loads((tmp_path / "cadastro.json").read_text(encoding="utf-8"))
    assert dados["chave"]
    assert dados["maquinas"]["computador-principal"]["papel"] == "principal"
    assert "aviso" not in dados
    assert not (tmp_path / ".config" / "castor" / "cofre").exists()


def test_configurar_google_grava_cofre_e_nao_imprime_senha(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "castor.configurar.entrada",
        io.StringIO("c\ncomputador-principal\ns\ng\nana@gmail.com\nsenha-secreta\n"),
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
            "ana@exemplo.test\nsegredo\n\n\n"
        ),
    )
    monkeypatch.setattr("castor.configurar.garantir_rede", lambda **_: None)
    assert principal(["configurar"]) == 0
    dados = json.loads((tmp_path / "cadastro.json").read_text(encoding="utf-8"))
    assert dados["aviso"]["servidor"] == "smtp.exemplo.test"


def test_configurar_sem_rede_nao_grava(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CASTOR_CADASTRO", str(tmp_path / "cadastro.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("castor.configurar.entrada", io.StringIO("c\nx\nn\n"))

    def garantir(**_):
        raise ErroDeRede("preciso de sudo uma vez para instalar o Tailscale.")

    monkeypatch.setattr("castor.configurar.garantir_rede", garantir)
    assert principal(["configurar"]) == 1
    assert not (tmp_path / "cadastro.json").exists()
    assert "sudo" in capsys.readouterr().err
