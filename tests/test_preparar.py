import pytest

from castor import preparar
from castor.preparar import EfeitoNaoConfirmado, Passo, PassoNaoProvado


def test_passos_rodam_na_ordem_e_devolvem_o_que_provaram():
    feitos = []
    passos = [
        Passo("chave", fazer=lambda c: feitos.append("chave")),
        Passo("sudo", fazer=lambda c: feitos.append("sudo"), exige=("chave",)),
    ]
    assert preparar.executar(passos, contexto={}, relatar=lambda t: None) == [
        "chave", "sudo"]
    assert feitos == ["chave", "sudo"]


def test_passo_que_rodou_sem_efeito_para_o_roteiro():
    feitos = []
    passos = [
        Passo("chave", fazer=lambda c: feitos.append("chave"),
              conferir=lambda c: "o authorized_keys continua vazio"),
        Passo("sudo", fazer=lambda c: feitos.append("sudo"), exige=("chave",)),
    ]
    with pytest.raises(EfeitoNaoConfirmado) as erro:
        preparar.executar(passos, contexto={}, relatar=lambda t: None)
    assert "chave" in str(erro.value)
    assert feitos == ["chave"]


def test_a_queixa_da_conferencia_chega_inteira_a_quem_le():
    """Sem isto, 'o relógio está 600s fora' vira 'o efeito não apareceu'."""
    passos = [Passo("relogio", fazer=lambda c: None,
                    conferir=lambda c: "ligue a sincronização de hora")]
    with pytest.raises(EfeitoNaoConfirmado) as erro:
        preparar.executar(passos, contexto={}, relatar=lambda t: None)
    assert "ligue a sincronização de hora" in str(erro.value)


def test_ordem_nao_queima_a_ponte():
    """O passo que fecha o acesso antigo não roda se o novo não foi provado."""
    fechou = []
    passos = [
        Passo("instalar_chave", fazer=lambda c: None),
        Passo("provar_chave", fazer=lambda c: None,
              conferir=lambda c: "a conexão pela chave nova não respondeu"),
        Passo("encerrar_acesso_inicial", fazer=lambda c: fechou.append(True),
              exige=("provar_chave",)),
    ]
    with pytest.raises(EfeitoNaoConfirmado):
        preparar.executar(passos, contexto={}, relatar=lambda t: None)
    assert fechou == [], "o acesso antigo foi fechado sem o novo ter sido provado"


def test_passo_que_exige_prova_inexistente_e_erro_de_roteiro():
    passos = [Passo("encerrar", fazer=lambda c: None, exige=("provar_chave",))]
    with pytest.raises(PassoNaoProvado) as erro:
        preparar.executar(passos, contexto={}, relatar=lambda t: None)
    assert "provar_chave" in str(erro.value)


def test_passo_pendente_e_relatado_e_nao_prova_nada():
    ditos = []
    passos = [
        Passo("aviso", fazer=None, pendente="depende do castor segredos enviar"),
        Passo("depois", fazer=lambda c: None),
    ]
    provados = preparar.executar(passos, contexto={}, relatar=ditos.append)
    assert "aviso" not in provados
    assert any("segredos enviar" in dito for dito in ditos)


def test_conferencia_sem_queixa_deixa_o_passo_provado():
    passos = [Passo("chave", fazer=lambda c: None, conferir=lambda c: None)]
    assert preparar.executar(passos, contexto={}, relatar=lambda t: None) == ["chave"]
