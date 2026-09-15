from dataclasses import replace

from castor import manifesto as m
from castor.cadastro import origem_para_gravar, resolver


def test_castor_json_antigo_vence_quando_cadastro_json_nao_existe(tmp_path, monkeypatch):
    monkeypatch.delenv("CASTOR_CADASTRO", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    antigo = tmp_path / "castor" / "castor.json"
    antigo.parent.mkdir(parents=True)
    antigo.write_text('{"maquinas": {}}', encoding="utf-8")
    assert resolver() == antigo


def test_cadastro_json_vence_o_antigo(tmp_path, monkeypatch):
    monkeypatch.delenv("CASTOR_CADASTRO", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    pasta = tmp_path / "castor"
    pasta.mkdir()
    (pasta / "castor.json").write_text("{}", encoding="utf-8")
    novo = pasta / "cadastro.json"
    novo.write_text("{}", encoding="utf-8")
    assert resolver() == novo


def test_variavel_relativa_e_ignorada(tmp_path, monkeypatch):
    monkeypatch.setenv("CASTOR_CADASTRO", "relativo.json")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert resolver().is_absolute()


def test_gravar_pelo_antigo_escreve_cadastro_json(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("CASTOR_CADASTRO", raising=False)
    pasta = tmp_path / "castor"
    pasta.mkdir()
    antigo = pasta / "castor.json"
    antigo.write_text('{"maquinas": {"x": {}}}', encoding="utf-8")
    lido = replace(m.ler(antigo), origem=origem_para_gravar(antigo))
    m.gravar(lido)
    assert (pasta / "cadastro.json").exists()
    assert antigo.exists()
