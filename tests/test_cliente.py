import json

from castor import cliente
from castor.manifesto import Manifesto

DADOS = {
    "cofre": "/home/ana/.config/castor/cofre",
    "chave": "/home/ana/.ssh/castor",
    "maquinas": {
        "bancada": {"papel": "principal", "usuario": "ana", "casa": "/home/ana",
                    "sistema": "linux"},
        "represa": {"papel": "cliente", "usuario": "castor",
                    "casa": "/home/castor", "sistema": "linux",
                    "endereco": "represa.exemplo.test"},
        "moinho": {"papel": "cliente", "usuario": "castor",
                   "casa": "/home/castor", "sistema": "linux",
                   "endereco": "moinho.exemplo.test"},
    },
    "servicos": {"correio": {"chaves": ["SMTP_SENHA"],
                             "destino": "$HOME/.config/castor/correio.env"}},
    "aviso": {"servidor": "smtp.exemplo.test", "porta": 587,
              "usuario": "castor@exemplo.test", "de": "castor@exemplo.test",
              "para": "ana@exemplo.test",
              "arquivo_de_segredo": "$HOME/.config/castor/correio.env",
              "variavel": "SMTP_SENHA"},
    "rotinas": {"limpeza": {"quando": "0 3 * * *", "comando": "true",
                            "maquina": "represa"},
                "outra": {"quando": "0 4 * * *", "comando": "true",
                          "maquina": "moinho"}},
}


def manifesto(tmp_path):
    return Manifesto(origem=tmp_path / "castor.json", dados=DADOS)


def test_o_cofre_nunca_vai(tmp_path):
    montado = cliente.montar(manifesto(tmp_path), "represa")
    assert "cofre" not in montado
    assert "chave" not in montado


def test_a_cliente_nao_ve_as_outras_maquinas(tmp_path):
    montado = cliente.montar(manifesto(tmp_path), "represa")
    assert list(montado["maquinas"]) == ["represa"]


def test_a_cliente_nao_recebe_o_endereco_da_principal(tmp_path):
    """A cliente nunca acessa a principal — endereço dela ali é convite."""
    montado = json.dumps(cliente.montar(manifesto(tmp_path), "represa"))
    assert "bancada" not in montado
    assert "/home/ana" not in montado


def test_leva_so_as_rotinas_dela(tmp_path):
    montado = cliente.montar(manifesto(tmp_path), "represa")
    assert list(montado["rotinas"]) == ["limpeza"]


def test_o_aviso_vai_com_os_caminhos_resolvidos(tmp_path):
    montado = cliente.montar(manifesto(tmp_path), "represa")
    assert montado["aviso"]["arquivo_de_segredo"] == \
        "/home/castor/.config/castor/correio.env"
    assert "$" not in json.dumps(montado["aviso"])


def test_a_cliente_se_reconhece_como_cliente(tmp_path):
    montado = cliente.montar(manifesto(tmp_path), "represa")
    assert montado["maquinas"]["represa"]["papel"] == "cliente"
    assert montado["maquinas"]["represa"]["casa"] == "/home/castor"


def test_o_texto_e_json_valido_e_termina_com_quebra(tmp_path):
    texto = cliente.como_texto(manifesto(tmp_path), "represa")
    assert texto.endswith("\n")
    assert json.loads(texto)["maquinas"]["represa"]["usuario"] == "castor"


def test_o_destino_na_cliente_sai_da_casa_medida(tmp_path):
    assert cliente.destino_na_cliente(manifesto(tmp_path), "represa") == \
        "/home/castor/.config/castor/castor.json"
