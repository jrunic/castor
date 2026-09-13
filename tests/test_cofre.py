import pytest

from castor import cofre
from castor.cofre import ChaveAusenteNoCofre, CofreAusente, CofreFrouxo

CONTEUDO = (
    "# o cofre é editado à mão\n"
    "SMTP_SERVIDOR=smtp.exemplo.test\n"
    "SMTP_PORTA=587\n"
    "\n"
    'SMTP_SENHA="abacaxi-de-mentira-123"\n'
)


@pytest.fixture
def guardado(tmp_path):
    caminho = tmp_path / "cofre"
    caminho.write_text(CONTEUDO, encoding="utf-8")
    caminho.chmod(0o600)
    return caminho


def test_le_as_atribuicoes_ignorando_comentario_e_vazio(guardado):
    valores = cofre.ler(guardado)
    assert valores == {"SMTP_SERVIDOR": "smtp.exemplo.test",
                       "SMTP_PORTA": "587",
                       "SMTP_SENHA": "abacaxi-de-mentira-123"}


def test_cofre_legivel_por_outro_usuario_e_recusado(guardado):
    guardado.chmod(0o644)
    with pytest.raises(CofreFrouxo) as erro:
        cofre.ler(guardado)
    assert "chmod 600" in str(erro.value)


def test_cofre_que_nao_existe_diz_onde_deveria_estar(tmp_path):
    with pytest.raises(CofreAusente) as erro:
        cofre.ler(tmp_path / "cofre")
    assert str(tmp_path / "cofre") in str(erro.value)


def test_filtrar_devolve_so_as_chaves_do_servico(guardado):
    valores = cofre.ler(guardado)
    filtrado = cofre.filtrar(valores, ["SMTP_SENHA", "SMTP_PORTA"],
                             origem="/caminho/do/cofre")
    assert list(filtrado) == ["SMTP_SENHA", "SMTP_PORTA"]


def test_chave_que_falta_no_cofre_nomeia_a_chave_e_o_cofre(guardado):
    valores = cofre.ler(guardado)
    with pytest.raises(ChaveAusenteNoCofre) as erro:
        cofre.filtrar(valores, ["SMTP_SENHA", "TOKEN_QUE_NAO_EXISTE"],
                      origem="/caminho/do/cofre")
    mensagem = str(erro.value)
    assert "TOKEN_QUE_NAO_EXISTE" in mensagem
    assert "/caminho/do/cofre" in mensagem


def test_o_erro_de_chave_ausente_nao_lista_o_que_existe(guardado):
    """Listar as chaves presentes conta o que o cofre guarda a quem não sabe."""
    valores = cofre.ler(guardado)
    with pytest.raises(ChaveAusenteNoCofre) as erro:
        cofre.filtrar(valores, ["TOKEN_QUE_NAO_EXISTE"], origem="/c")
    assert "SMTP_SENHA" not in str(erro.value)
