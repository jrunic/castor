import json

import pytest

from castor import manifesto


def escrever(tmp_path, dados):
    caminho = tmp_path / "castor.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


def test_resolve_maquina_declarada_so_no_manifesto(tmp_path):
    caminho = escrever(tmp_path, {
        "maquinas": {
            "carvalho": {"usuario": "ana", "casa": "/home/ana", "sistema": "linux"},
        }
    })
    maquina = manifesto.ler(caminho).maquina("carvalho")
    assert maquina.casa == "/home/ana"
    assert maquina.usuario == "ana"


def test_maquina_ausente_nomeia_o_manifesto_e_a_chave(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {}})
    with pytest.raises(manifesto.MaquinaDesconhecida) as erro:
        manifesto.ler(caminho).maquina("cedro")
    mensagem = str(erro.value)
    assert "cedro" in mensagem
    assert str(caminho) in mensagem
