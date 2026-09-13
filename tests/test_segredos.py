import subprocess

import pytest

from castor import segredos
from castor.manifesto import Manifesto

PRINCIPAL_CASA = "/home/ana"
CLIENTE_CASA = "/home/castor"
SENHA_SINTETICA = "abacaxi-de-mentira-123"

VALORES = {"SMTP_SERVIDOR": "smtp.exemplo.test", "SMTP_PORTA": "587",
           "SMTP_SENHA": SENHA_SINTETICA, "TOKEN_DE_OUTRO": "nao-e-deste"}


def manifesto_de(tmp_path, servicos=None):
    dados = {
        "maquinas": {
            "bancada": {"papel": "principal", "usuario": "ana",
                        "casa": PRINCIPAL_CASA, "sistema": "linux"},
            "represa": {"papel": "cliente", "usuario": "castor",
                        "casa": CLIENTE_CASA, "sistema": "linux",
                        "endereco": "represa.exemplo.test"},
        },
        "servicos": servicos if servicos is not None else {
            "correio": {"chaves": ["SMTP_SERVIDOR", "SMTP_PORTA", "SMTP_SENHA"],
                        "destino": "$HOME/.config/castor/correio.env"},
        },
    }
    return Manifesto(origem=tmp_path / "castor.json", dados=dados)


def test_o_conteudo_traz_so_as_chaves_do_servico(tmp_path):
    conteudo = segredos.montar(manifesto_de(tmp_path), "correio", "represa",
                               VALORES)
    assert "TOKEN_DE_OUTRO" not in conteudo
    assert conteudo.splitlines() == [
        'SMTP_SERVIDOR="smtp.exemplo.test"',
        'SMTP_PORTA="587"',
        f'SMTP_SENHA="{SENHA_SINTETICA}"',
    ]


def test_o_conteudo_e_lido_por_shell(tmp_path):
    conteudo = segredos.montar(manifesto_de(tmp_path), "correio", "represa",
                               VALORES)
    arquivo = tmp_path / "correio.env"
    arquivo.write_text(conteudo, encoding="utf-8")
    lido = subprocess.run(
        ["sh", "-c", f'. {arquivo} && printf %s "$SMTP_SENHA"'],
        capture_output=True, text=True)
    assert lido.stdout == SENHA_SINTETICA


def test_o_conteudo_serve_de_environmentfile(tmp_path):
    conteudo = segredos.montar(manifesto_de(tmp_path), "correio", "represa",
                               VALORES)
    for linha in conteudo.splitlines():
        assert not linha.startswith("export ")
        assert "$" not in linha and "`" not in linha
        assert linha.split("=", 1)[0].replace("_", "").isalnum()


def test_home_no_valor_vira_a_casa_da_maquina_que_vai_usar(tmp_path):
    valores = {**VALORES, "PASTA": "$HOME/dados"}
    manifesto = manifesto_de(tmp_path, servicos={
        "correio": {"chaves": ["PASTA"], "destino": "$HOME/correio.env"}})
    conteudo = segredos.montar(manifesto, "correio", "represa", valores)
    assert conteudo.strip() == f'PASTA="{CLIENTE_CASA}/dados"'


def test_home_principal_no_valor_vira_a_casa_da_principal(tmp_path):
    valores = {"PASTA": "$HOME_PRINCIPAL/dados"}
    manifesto = manifesto_de(tmp_path, servicos={
        "correio": {"chaves": ["PASTA"], "destino": "$HOME/correio.env"}})
    conteudo = segredos.montar(manifesto, "correio", "represa", valores)
    assert conteudo.strip() == f'PASTA="{PRINCIPAL_CASA}/dados"'


def test_o_destino_tambem_resolve_a_marca(tmp_path):
    destino = segredos.destino_de(manifesto_de(tmp_path), "correio", "represa")
    assert destino == f"{CLIENTE_CASA}/.config/castor/correio.env"


def test_servico_que_nao_esta_no_manifesto_nomeia_o_manifesto(tmp_path):
    with pytest.raises(segredos.ServicoDesconhecido) as erro:
        segredos.montar(manifesto_de(tmp_path), "inexistente", "represa", VALORES)
    assert "inexistente" in str(erro.value)
    assert "servicos" in str(erro.value)


def test_a_soma_muda_quando_o_valor_muda(tmp_path):
    manifesto = manifesto_de(tmp_path)
    um = segredos.soma(segredos.montar(manifesto, "correio", "represa", VALORES))
    outro = segredos.soma(segredos.montar(
        manifesto, "correio", "represa", {**VALORES, "SMTP_SENHA": "outra"}))
    assert um != outro
    assert len(um) == 64


def test_ver_continua_descrevendo_sem_revelar(tmp_path):
    """Contrato usado pelo aviso da rotina na cliente — não muda em silêncio."""
    arquivo = tmp_path / "correio.env"
    arquivo.write_text(f'SMTP_SENHA="{SENHA_SINTETICA}"\n', encoding="utf-8")
    relato = segredos.ver(arquivo, "SMTP_SENHA")
    assert SENHA_SINTETICA not in relato
    assert str(len(SENHA_SINTETICA)) in relato
    assert segredos.ver(arquivo, "SMTP_SENHA", revelar=True) == SENHA_SINTETICA


def test_variavel_ausente_nomeia_o_arquivo(tmp_path):
    arquivo = tmp_path / "correio.env"
    arquivo.write_text("OUTRA=coisa\n", encoding="utf-8")
    with pytest.raises(segredos.VariavelAusente) as erro:
        segredos.ver(arquivo, "SMTP_SENHA")
    assert str(arquivo) in str(erro.value)
