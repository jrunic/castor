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


def test_principal_e_a_maquina_declarada_como_tal(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {
        "bancada": {"papel": "principal", "usuario": "ana", "casa": "/Users/ana",
                    "sistema": "darwin"},
        "represa": {"papel": "cliente", "usuario": "castor", "casa": "/home/castor",
                    "sistema": "linux", "endereco": "represa.exemplo.test"},
    }})
    principal = manifesto.ler(caminho).principal()
    assert principal.nome == "bancada"
    assert principal.papel == "principal"


def test_manifesto_sem_principal_diz_o_que_fazer(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {}})
    with pytest.raises(manifesto.SemPrincipal) as erro:
        manifesto.ler(caminho).principal()
    assert "castor maquina adicionar" in str(erro.value)


def test_cliente_conhece_endereco_e_a_principal_nao_precisa(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {
        "represa": {"papel": "cliente", "usuario": "castor", "casa": "/home/castor",
                    "sistema": "linux", "endereco": "represa.exemplo.test"},
    }})
    cliente = manifesto.ler(caminho).maquina("represa")
    assert cliente.endereco == "represa.exemplo.test"
    assert cliente.papel == "cliente"


def test_acrescentar_maquina_grava_e_releitura_enxerga(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {}})
    lido = manifesto.ler(caminho)
    manifesto.gravar(manifesto.acrescentar(lido, manifesto.Maquina(
        nome="represa", usuario="castor", casa="/home/castor", sistema="linux",
        papel="cliente", endereco="represa.exemplo.test", python="3.14.0")))
    assert manifesto.ler(caminho).maquina("represa").python == "3.14.0"


def test_acrescentar_maquina_ja_declarada_e_recusado(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {
        "represa": {"papel": "cliente", "usuario": "castor", "casa": "/home/castor",
                    "sistema": "linux", "endereco": "represa.exemplo.test"}}})
    lido = manifesto.ler(caminho)
    nova = manifesto.Maquina(nome="represa", usuario="outro", casa="/home/outro",
                             sistema="linux", papel="cliente",
                             endereco="outro.exemplo.test")
    with pytest.raises(manifesto.MaquinaJaDeclarada):
        manifesto.acrescentar(lido, nova)


def test_retirar_tira_a_maquina_e_recusa_a_que_nao_existe(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {
        "represa": {"papel": "cliente", "usuario": "castor", "casa": "/home/castor",
                    "sistema": "linux", "endereco": "represa.exemplo.test"}}})
    lido = manifesto.ler(caminho)
    assert manifesto.retirar(lido, "represa").nomes() == []
    with pytest.raises(manifesto.MaquinaDesconhecida):
        manifesto.retirar(lido, "moinho")


def test_gravar_nao_deixa_arquivo_pela_metade(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {}})
    lido = manifesto.ler(caminho)
    manifesto.gravar(lido)
    assert not list(tmp_path.glob("*.novo"))
    json.loads(caminho.read_text(encoding="utf-8"))


def test_anotar_guarda_o_caminho_da_chave(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {}})
    lido = manifesto.ler(caminho)
    manifesto.gravar(manifesto.anotar(lido, "chave", "/tmp/chave-de-teste"))
    from pathlib import Path
    assert manifesto.ler(caminho).caminho_da_chave() == Path("/tmp/chave-de-teste")


def test_manifesto_sem_chave_declarada_nao_inventa_caminho(tmp_path):
    caminho = escrever(tmp_path, {"maquinas": {}})
    assert manifesto.ler(caminho).caminho_da_chave() is None


def test_ler_arquivo_ausente_diz_qual_comando_cria(tmp_path):
    with pytest.raises(manifesto.ErroDeManifesto) as erro:
        manifesto.ler(tmp_path / "castor.json")
    assert "castor maquina adicionar" in str(erro.value)


def test_ler_ou_vazio_nasce_sem_maquina_nenhuma(tmp_path):
    lido = manifesto.ler_ou_vazio(tmp_path / "castor.json")
    assert lido.nomes() == []
    assert lido.origem == tmp_path / "castor.json"
