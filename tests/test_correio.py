from castor.correio import Aviso, montar_mensagem


def test_mensagem_traz_alarme_maquina_e_saida():
    aviso = Aviso(
        alarme="rotina.backup.falhou",
        maquina="carvalho",
        assunto_extra="código 2",
        corpo="linha um\nlinha dois",
    )
    mensagem = montar_mensagem(aviso, de="castor@exemplo.test", para="ana@exemplo.test")

    assert mensagem["To"] == "ana@exemplo.test"
    assert "rotina.backup.falhou" in mensagem["Subject"]
    assert "carvalho" in mensagem["Subject"]
    assert "linha dois" in mensagem.get_content()


def test_corpo_muito_longo_e_truncado_no_fim():
    aviso = Aviso(alarme="a", maquina="m", assunto_extra="", corpo="x" * 9000)
    mensagem = montar_mensagem(aviso, de="c@t.test", para="a@t.test")
    conteudo = mensagem.get_content()
    assert len(conteudo) < 9000
    assert "truncado" in conteudo


from castor.correio import RemetenteSMTP


class ClienteDeMentira:
    def __init__(self):
        self.autenticou = None
        self.enviou = None
        self.fechou = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechou = True

    def starttls(self):
        pass

    def login(self, usuario, senha):
        self.autenticou = (usuario, senha)

    def send_message(self, mensagem):
        self.enviou = mensagem


def test_remetente_autentica_e_envia():
    cliente = ClienteDeMentira()
    remetente = RemetenteSMTP(
        servidor="smtp.exemplo.test", porta=587,
        usuario="ana", senha="abacaxi-de-mentira",
        abrir=lambda servidor, porta: cliente,
    )
    mensagem = montar_mensagem(
        Aviso(alarme="a", maquina="m", assunto_extra="", corpo="c"),
        de="c@t.test", para="a@t.test",
    )

    remetente.enviar(mensagem)

    assert cliente.autenticou == ("ana", "abacaxi-de-mentira")
    assert cliente.enviou is mensagem
    assert cliente.fechou is True


def test_senha_nao_aparece_na_representacao_do_remetente():
    remetente = RemetenteSMTP(servidor="s", porta=1, usuario="u",
                              senha="abacaxi-de-mentira", abrir=lambda *_: None)
    assert "abacaxi-de-mentira" not in repr(remetente)
