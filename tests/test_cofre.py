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


from castor.cofre import ValorHostil  # noqa: E402


def test_home_vira_o_diretorio_da_maquina_que_vai_usar():
    resolvido = cofre.resolver("$HOME/.config/castor/correio.env",
                               casa="/home/castor", casa_principal="/home/ana")
    assert resolvido == "/home/castor/.config/castor/correio.env"


def test_home_principal_vira_o_diretorio_da_principal():
    resolvido = cofre.resolver("$HOME_PRINCIPAL/cofre",
                               casa="/home/castor", casa_principal="/home/ana")
    assert resolvido == "/home/ana/cofre"


def test_a_marca_longa_nao_e_comida_pela_curta():
    """$HOME_PRINCIPAL resolvido pela regra de $HOME viraria /home/ana_PRINCIPAL."""
    resolvido = cofre.resolver("$HOME_PRINCIPAL", casa="/home/castor",
                               casa_principal="/home/ana")
    assert resolvido == "/home/ana"
    assert "_PRINCIPAL" not in resolvido


def test_as_duas_marcas_na_mesma_linha():
    resolvido = cofre.resolver("$HOME/de/$HOME_PRINCIPAL", casa="/c",
                               casa_principal="/p")
    assert resolvido == "/c/de//p"


def test_palavra_que_comeca_com_home_nao_e_marca():
    with pytest.raises(ValorHostil):
        cofre.resolver("$HOMEX", casa="/c", casa_principal="/p")


def test_marca_entre_chaves_nao_e_aceita():
    """Uma sintaxe só. Duas convidam a decorar qual delas funciona."""
    with pytest.raises(ValorHostil) as erro:
        cofre.resolver("${HOME}/x", casa="/c", casa_principal="/p")
    assert "$HOME" in str(erro.value)


def test_cifrao_que_sobra_e_recusado():
    with pytest.raises(ValorHostil) as erro:
        cofre.resolver("a$USER-b", casa="/c", casa_principal="/p")
    assert "shell" in str(erro.value)


def test_crase_e_recusada():
    with pytest.raises(ValorHostil):
        cofre.resolver("a`whoami`b", casa="/c", casa_principal="/p")


def test_valor_sem_marca_nenhuma_atravessa_inteiro():
    assert cofre.resolver("abacaxi-123", casa="/c", casa_principal="/p") == \
        "abacaxi-123"
