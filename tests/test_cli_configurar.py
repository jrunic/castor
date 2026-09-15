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
