import json

import pytest

from castor import ronda
from castor.ronda import ChecagemInvalida, Resultado


def test_comando_que_sai_zero_passou():
    resultado = ronda.avaliar_comando("disco", saida_codigo=0, texto="")
    assert resultado.passou
    assert resultado.nome == "disco"


def test_comando_que_sai_diferente_de_zero_falhou_e_diz_o_codigo():
    resultado = ronda.avaliar_comando("disco", saida_codigo=1, texto="91")
    assert not resultado.passou
    assert "1" in resultado.detalhe


def test_comando_inexistente_falha_como_qualquer_outro():
    """127 não é zero. Comando errado é falha, não exceção."""
    resultado = ronda.avaliar_comando("disco", saida_codigo=127,
                                      texto="command not found")
    assert not resultado.passou


def test_servico_ativo_passou():
    assert ronda.avaliar_servico("sentinela", "active").passou


def test_servico_em_qualquer_outro_estado_falhou():
    for situacao in ("inactive", "failed", "activating", ""):
        resultado = ronda.avaliar_servico("sentinela", situacao)
        assert not resultado.passou, situacao
        assert situacao in resultado.detalhe or "vazio" in resultado.detalhe


def test_expiracao_desativada_passou():
    assert ronda.avaliar_expiracao("represa", None).passou


def test_expiracao_ativa_falhou_e_diz_a_data():
    resultado = ronda.avaliar_expiracao("represa", "2026-12-16T13:48:07Z")
    assert not resultado.passou
    assert "2026-12-16" in resultado.detalhe


def test_checagem_sem_tipo_e_recusada():
    with pytest.raises(ChecagemInvalida) as erro:
        ronda.conferir_declaracao("x", {"maquina": "represa"})
    assert "tipo" in str(erro.value)


def test_tipo_desconhecido_e_recusado_nomeando_os_que_existem():
    with pytest.raises(ChecagemInvalida) as erro:
        ronda.conferir_declaracao("x", {"tipo": "telepatia", "maquina": "r"})
    assert "comando" in str(erro.value) and "expiracao" in str(erro.value)


def test_checagem_de_comando_sem_comando_e_recusada():
    with pytest.raises(ChecagemInvalida) as erro:
        ronda.conferir_declaracao("x", {"tipo": "comando", "maquina": "r"})
    assert "comando" in str(erro.value)


def test_checagem_de_servico_sem_servico_e_recusada():
    with pytest.raises(ChecagemInvalida) as erro:
        ronda.conferir_declaracao("x", {"tipo": "servico", "maquina": "r"})
    assert "servico" in str(erro.value)


def test_checagem_sem_maquina_e_recusada():
    with pytest.raises(ChecagemInvalida) as erro:
        ronda.conferir_declaracao("x", {"tipo": "expiracao"})
    assert "maquina" in str(erro.value)


def test_maquina_inalcancavel_e_uma_falha_so():
    """Sem isto, máquina fora do ar manda um e-mail por checagem dela."""
    declaradas = {
        "a": {"tipo": "comando", "maquina": "represa", "comando": "true"},
        "b": {"tipo": "servico", "maquina": "represa", "servico": "x"},
    }
    resultados = ronda.maquina_inalcancavel("represa", declaradas,
                                            "não respondeu")
    assert len(resultados) == 1
    assert not resultados[0].passou
    assert "represa" in resultados[0].nome


def test_gravar_e_ler_a_ultima_ronda(tmp_path):
    arquivo = tmp_path / "ronda.json"
    resultados = [Resultado("disco", True, ""),
                  Resultado("sentinela", False, "está 'failed'")]
    ronda.gravar(arquivo, resultados, agora=1789000000.0)

    lido = ronda.ultima(arquivo)
    assert lido["quando"] == 1789000000.0
    assert lido["resultados"][1]["detalhe"] == "está 'failed'"


def test_ler_sem_ronda_anterior_nao_explode(tmp_path):
    assert ronda.ultima(tmp_path / "nao-existe.json") is None


def test_gravar_nao_deixa_arquivo_pela_metade(tmp_path):
    arquivo = tmp_path / "ronda.json"
    ronda.gravar(arquivo, [Resultado("x", True, "")], agora=1.0)
    assert not list(tmp_path.glob("*.novo"))
    json.loads(arquivo.read_text(encoding="utf-8"))


def test_quem_falhou_agora_e_nao_falhava_antes():
    """É o que decide se avisa: mudou de estado, não apenas está mal."""
    antes = [Resultado("a", False, ""), Resultado("b", True, "")]
    agora = [Resultado("a", False, ""), Resultado("b", False, "")]
    assert ronda.piorou(antes, agora) == ["b"]


def test_quem_voltou_ao_normal():
    antes = [Resultado("a", False, ""), Resultado("b", False, "")]
    agora = [Resultado("a", True, ""), Resultado("b", False, "")]
    assert ronda.melhorou(antes, agora) == ["a"]


def test_sem_ronda_anterior_tudo_que_falha_piorou():
    agora = [Resultado("a", False, ""), Resultado("b", True, "")]
    assert ronda.piorou(None, agora) == ["a"]


def test_comparar_o_que_veio_do_arquivo_com_o_que_acabou_de_rodar(tmp_path):
    """É esta a forma real: dicionário lido do JSON contra Resultado novo.

    A comparação atravessa uma volta por arquivo, e é ali que a diferença entre
    r.passou e r["passou"] quebra — provar só Resultado contra Resultado deixa
    justamente o caminho de produção sem teste.
    """
    arquivo = tmp_path / "ronda.json"
    ronda.gravar(arquivo, [Resultado("a", False, ""), Resultado("b", True, "")],
                 agora=1.0)
    lido = ronda.ultima(arquivo)["resultados"]
    agora = [Resultado("a", False, ""), Resultado("b", False, "")]
    assert ronda.piorou(lido, agora) == ["b"]
    assert ronda.melhorou(lido, agora) == []
