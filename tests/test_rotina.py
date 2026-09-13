import subprocess
import sys
import textwrap
import time
from pathlib import Path

from castor.rotina import Resultado, rodar
from castor.supressao import Supressor


class RemetenteDeMentira:
    def __init__(self):
        self.enviadas = []

    def enviar(self, mensagem):
        self.enviadas.append(mensagem)


def test_sucesso_devolve_zero_e_registra_a_saida(tmp_path):
    registro = tmp_path / "backup.log"
    resultado = rodar("backup", ["sh", "-c", "echo feito"], registro=registro,
                      trava=tmp_path / "backup.trava")
    assert isinstance(resultado, Resultado)
    assert resultado.codigo == 0
    assert "feito" in registro.read_text(encoding="utf-8")


def test_falha_preserva_o_codigo_do_comando(tmp_path):
    resultado = rodar("backup", ["sh", "-c", "exit 3"], registro=tmp_path / "b.log",
                      trava=tmp_path / "b.trava")
    assert resultado.codigo == 3
    assert resultado.falhou is True


def test_registro_acumula_entre_execucoes(tmp_path):
    registro = tmp_path / "b.log"
    trava = tmp_path / "b.trava"
    rodar("backup", ["sh", "-c", "echo primeira"], registro=registro, trava=trava)
    rodar("backup", ["sh", "-c", "echo segunda"], registro=registro, trava=trava)
    conteudo = registro.read_text(encoding="utf-8")
    assert "primeira" in conteudo and "segunda" in conteudo


def test_segunda_execucao_simultanea_nao_roda(tmp_path):
    trava = tmp_path / "b.trava"
    registro = tmp_path / "b.log"
    marca = tmp_path / "entrou"
    sentinela = tmp_path / "segurando"

    codigo = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(Path("src").resolve())!r})
        from castor.rotina import rodar
        rodar("backup", ["sh", "-c", "touch {sentinela}; sleep 2"],
              registro={str(registro)!r}, trava={str(trava)!r})
    """)
    primeiro = subprocess.Popen([sys.executable, "-c", codigo])
    try:
        # A sentinela só existe depois que a trava foi adquirida — esperar o
        # arquivo da trava aparecer não provaria nada.
        for _ in range(200):
            if sentinela.exists():
                break
            time.sleep(0.05)

        segundo = rodar("backup", ["sh", "-c", f"touch {marca}"],
                        registro=registro, trava=trava)
        assert segundo.nao_rodou_por_trava is True
        assert not marca.exists(), "o comando rodou apesar da trava"
    finally:
        primeiro.wait(timeout=10)


def test_teto_de_tempo_encerra_e_marca(tmp_path):
    resultado = rodar("demorado", ["sh", "-c", "sleep 5"],
                      registro=tmp_path / "d.log", trava=tmp_path / "d.trava",
                      teto_em_segundos=1)
    assert resultado.estourou_o_tempo is True
    assert resultado.falhou is True
    assert "tempo" in resultado.saida.lower()


def test_teto_estourado_tambem_avisa(tmp_path):
    remetente = RemetenteDeMentira()
    rodar("demorado", ["sh", "-c", "sleep 5"], registro=tmp_path / "d.log",
          trava=tmp_path / "d.trava", teto_em_segundos=1, remetente=remetente,
          supressor=Supressor(tmp_path / "a.json", janela_em_minutos=60),
          de="c@t.test", para="a@t.test", maquina="carvalho", agora=1_000_000)
    assert len(remetente.enviadas) == 1
    assert "tempo estourado" in remetente.enviadas[0]["Subject"]


def test_falha_avisa_uma_vez_por_janela(tmp_path):
    remetente = RemetenteDeMentira()
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    comum = dict(registro=tmp_path / "b.log", trava=tmp_path / "b.trava",
                 remetente=remetente, supressor=supressor,
                 de="castor@t.test", para="ana@t.test", maquina="carvalho")

    for momento in (1_000_000, 1_000_060, 1_000_120):
        rodar("backup", ["sh", "-c", "exit 1"], agora=momento, **comum)

    assert len(remetente.enviadas) == 1, "três falhas na janela deveriam render um aviso"
    assert "backup" in remetente.enviadas[0]["Subject"]


def test_sucesso_nao_avisa(tmp_path):
    remetente = RemetenteDeMentira()
    rodar("backup", ["sh", "-c", "exit 0"], registro=tmp_path / "b.log",
          trava=tmp_path / "b.trava", remetente=remetente,
          supressor=Supressor(tmp_path / "a.json", janela_em_minutos=60),
          de="c@t.test", para="a@t.test", maquina="carvalho", agora=1_000_000)
    assert remetente.enviadas == []


def test_falha_depois_da_janela_avisa_de_novo(tmp_path):
    remetente = RemetenteDeMentira()
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)
    comum = dict(registro=tmp_path / "b.log", trava=tmp_path / "b.trava",
                 remetente=remetente, supressor=supressor,
                 de="c@t.test", para="a@t.test", maquina="carvalho")

    rodar("backup", ["sh", "-c", "exit 1"], agora=1_000_000, **comum)
    rodar("backup", ["sh", "-c", "exit 1"], agora=1_000_000 + 3601, **comum)

    assert len(remetente.enviadas) == 2


class RemetenteQueCai:
    """O servidor de e-mail fora do ar, que é o caso comum quando algo falha."""

    def __init__(self):
        self.tentou = False

    def enviar(self, mensagem):
        self.tentou = True
        raise OSError("[Errno 8] nodename nor servname provided")


def test_correio_fora_do_ar_nao_engole_o_codigo_da_rotina(tmp_path):
    """A rotina falhou com 2; o aviso falhar não pode virar rastreamento.

    Quem chama é o cron. Rastreamento no lugar do código de saída faz a falha
    da rotina virar falha do castor, e o diagnóstico vai para o lugar errado.
    """
    remetente = RemetenteQueCai()
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)

    resultado = rodar(
        "limpeza", ["sh", "-c", "echo falhei >&2; exit 2"],
        registro=tmp_path / "registro.log", trava=tmp_path / "trava",
        remetente=remetente, supressor=supressor, de="a@t.test", para="b@t.test",
        maquina="represa", agora=1000.0)

    assert remetente.tentou
    assert resultado.codigo == 2


def test_falha_no_envio_nao_marca_o_alarme_como_avisado(tmp_path):
    """Senão o primeiro aviso que der certo seria suprimido pelo que falhou."""
    supressor = Supressor(tmp_path / "avisos.json", janela_em_minutos=60)

    rodar("limpeza", ["sh", "-c", "exit 2"],
                 registro=tmp_path / "registro.log", trava=tmp_path / "trava",
                 remetente=RemetenteQueCai(), supressor=supressor,
                 de="a@t.test", para="b@t.test", maquina="represa", agora=1000.0)

    assert supressor.pode_avisar("rotina.limpeza.falhou", agora=1001.0)
