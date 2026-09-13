from castor.supressao import Supressor


def test_primeiro_aviso_passa(tmp_path):
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    assert supressor.pode_avisar("rotina.backup.falhou", agora=1_000_000) is True


def test_segundo_aviso_na_janela_nao_passa(tmp_path):
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    supressor.registrar("rotina.backup.falhou", agora=1_000_000)
    assert supressor.pode_avisar("rotina.backup.falhou", agora=1_000_000 + 60) is False


def test_alarme_diferente_nao_e_suprimido(tmp_path):
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    supressor.registrar("rotina.backup.falhou", agora=1_000_000)
    assert supressor.pode_avisar("ronda.disco.cheio", agora=1_000_000 + 60) is True


def test_janela_vencida_volta_a_avisar(tmp_path):
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    supressor.registrar("rotina.backup.falhou", agora=1_000_000)
    depois = 1_000_000 + 60 * 60 + 1
    assert supressor.pode_avisar("rotina.backup.falhou", agora=depois) is True


def test_estado_sobrevive_a_troca_de_processo(tmp_path):
    caminho = tmp_path / "avisos.json"
    Supressor(caminho, janela_em_minutos=60).registrar("a", agora=1_000_000)
    assert Supressor(caminho, janela_em_minutos=60).pode_avisar("a", agora=1_000_030) is False


def test_estado_corrompido_nao_impede_o_aviso(tmp_path):
    caminho = tmp_path / "avisos.json"
    caminho.write_text("{ isto não é json", encoding="utf-8")
    assert Supressor(caminho, janela_em_minutos=60).pode_avisar("a", agora=1) is True


def test_esquecer_deixa_o_proximo_aviso_passar(tmp_path):
    """Depois de 'voltou ao normal', uma falha nova não pode ficar muda."""
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    assert supressor.pode_avisar("ronda.disco.falhou", agora=1000.0)
    supressor.registrar("ronda.disco.falhou", agora=1000.0)
    assert not supressor.pode_avisar("ronda.disco.falhou", agora=1060.0)

    supressor.esquecer("ronda.disco.falhou")
    assert supressor.pode_avisar("ronda.disco.falhou", agora=1060.0)


def test_esquecer_alarme_que_nunca_avisou_nao_explode(tmp_path):
    Supressor(tmp_path / "avisos.json", janela_em_minutos=60).esquecer("nunca")
