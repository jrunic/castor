import pytest

from castor.expansao import MarcaDesconhecida, expandir
from castor.manifesto import Maquina

MAQUINA = Maquina(nome="carvalho", usuario="ana", casa="/home/ana", sistema="linux")


@pytest.mark.parametrize("modelo,esperado", [
    ("CAMINHO=%{CASA}/dados", "CAMINHO=/home/ana/dados"),
    ("DONO=%{USUARIO}", "DONO=ana"),
    ("ONDE=%{MAQUINA}", "ONDE=carvalho"),
    ("DUAS=%{CASA}:%{USUARIO}", "DUAS=/home/ana:ana"),
    ("SO=%{SISTEMA}", "SO=linux"),
    ("SEM_MARCA=valor", "SEM_MARCA=valor"),
])
def test_expande_cada_marca(modelo, esperado):
    assert expandir(modelo, MAQUINA) == esperado


def test_marca_desconhecida_falha_nomeando_a_marca():
    with pytest.raises(MarcaDesconhecida) as erro:
        expandir("X=%{PORTA}", MAQUINA)
    assert "PORTA" in str(erro.value)
