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


from castor import conexao  # noqa: E402

RESPOSTA_MEDIDA = (
    "usuario=castor-inicial\ncasa=/home/castor-inicial\nsistema=Linux\n"
    "epoca=1789000000\nfuso=-0400\npython=Python 3.14.0\nsudo=nao\n"
)


class ConexaoDeMentira:
    """Responde como a máquina responderia, e guarda COMO foi chamada."""

    def __init__(self, respostas=None):
        self.respostas = respostas or {}
        self.chamadas = []

    def __call__(self, destino, comando, **opcoes):
        self.chamadas.append((destino.usuario, comando, opcoes))
        for gatilho, resposta in self.respostas.items():
            if gatilho in comando:
                return conexao.Saida(codigo=0, texto=resposta, erro="")
        if comando == "id -un":
            # A máquina responde o usuário DA CONEXÃO — e é disso que a prova
            # da chave depende. Mock que responde igual aos dois usuários
            # esconderia justamente o passo que separa um do outro.
            return conexao.Saida(codigo=0, texto=f"{destino.usuario}\n", erro="")
        return conexao.Saida(codigo=0, texto="", erro="")


def _roteiro(executor, contexto=None, agora=lambda: 1789000000):
    return preparar.montar_roteiro(
        nome="represa", endereco="represa.exemplo.test",
        usuario_inicial="castor-inicial", usuario_de_servico="castor",
        chave_publica="ssh-ed25519 AAAA... ana",
        contexto=contexto if contexto is not None else {}, executor=executor,
        agora=agora)


def test_roteiro_comeca_pelo_acesso_inicial_e_so_depois_mede():
    nomes = [passo.nome for passo in _roteiro(ConexaoDeMentira())]
    assert nomes[:5] == ["acesso_inicial", "identidade", "relogio", "python",
                         "usuario_de_servico"]
    for esperado in ("provar_chave", "sudo", "instalar_castor", "rede",
                     "expiracao", "aviso"):
        assert esperado in nomes


def test_o_primeiro_acesso_repassa_o_terminal_para_a_senha():
    executor = ConexaoDeMentira()
    roteiro = {p.nome: p for p in _roteiro(executor)}
    roteiro["acesso_inicial"].fazer({})
    usuario, _, opcoes = executor.chamadas[0]
    assert usuario == "castor-inicial"
    assert opcoes.get("com_senha") is True


def test_os_passos_com_sudo_do_usuario_inicial_pedem_terminal_uma_vez_so():
    executor = ConexaoDeMentira()
    roteiro = {p.nome: p for p in _roteiro(executor)}
    roteiro["usuario_de_servico"].fazer({})
    com_sudo = [c for c in executor.chamadas if "sudo" in c[1]]
    assert len(com_sudo) == 1, "mais de um sudo é mais de um pedido de senha"
    assert com_sudo[0][2].get("com_terminal") is True


def test_a_medicao_roda_por_chave_e_nao_por_senha():
    """Com terminal repassado não há texto de volta — a sonda ficaria vazia."""
    executor = ConexaoDeMentira({"usuario=": RESPOSTA_MEDIDA})
    contexto = {}
    roteiro = {p.nome: p for p in _roteiro(executor, contexto)}
    roteiro["identidade"].fazer(contexto)
    _, _, opcoes = executor.chamadas[-1]
    assert not opcoes.get("com_senha") and not opcoes.get("com_terminal")
    assert contexto["medicao"].usuario == "castor-inicial"


def test_a_rede_exige_o_sudo_sem_senha_para_poder_capturar_a_url():
    roteiro = {p.nome: p for p in _roteiro(ConexaoDeMentira())}
    assert "sudo" in roteiro["rede"].exige


def test_encerrar_acesso_inicial_exige_a_prova_da_chave():
    roteiro = {p.nome: p for p in _roteiro(ConexaoDeMentira())}
    assert "provar_chave" in roteiro["encerrar_acesso_inicial"].exige


def test_passo_do_aviso_fica_pendente_ate_o_envio_de_segredos_existir():
    roteiro = {p.nome: p for p in _roteiro(ConexaoDeMentira())}
    assert roteiro["aviso"].pendente
    assert "segredos enviar" in roteiro["aviso"].pendente


def test_a_url_de_login_capturada_vai_para_o_contexto():
    saida = "To authenticate, visit:\n\thttps://login.tailscale.com/a/1a2b3c\n"
    executor = ConexaoDeMentira({"tailscale up": saida})
    contexto = {}
    roteiro = {p.nome: p for p in _roteiro(executor, contexto)}
    roteiro["rede"].fazer(contexto)
    assert contexto["url_de_login"] == "https://login.tailscale.com/a/1a2b3c"


def test_a_prova_da_chave_falha_quando_a_maquina_responde_outro_usuario():
    executor = ConexaoDeMentira({"id -un": "outro\n"})
    contexto = {}
    roteiro = {p.nome: p for p in _roteiro(executor, contexto)}
    roteiro["provar_chave"].fazer(contexto)
    queixa = roteiro["provar_chave"].conferir(contexto)
    assert "outro" in queixa
    assert "continua de pé" in queixa


def test_o_roteiro_inteiro_roda_e_nao_chega_a_fechar_o_acesso_inicial():
    """Tracer bullet: do primeiro acesso à rede, com a máquina de mentira."""
    executor = ConexaoDeMentira({
        "usuario=": RESPOSTA_MEDIDA,
        "tailscale up": "visit: https://login.tailscale.com/a/9z8y\n",
    })
    contexto = {}
    provados = preparar.executar(_roteiro(executor, contexto), contexto,
                                 relatar=lambda t: None)
    assert provados == ["acesso_inicial", "identidade", "relogio", "python",
                        "usuario_de_servico", "provar_chave", "sudo",
                        "instalar_castor", "rede"]
    assert "encerrar_acesso_inicial" not in provados
    assert contexto["url_de_login"].endswith("9z8y")
