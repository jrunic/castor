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
