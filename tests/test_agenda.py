import os
import shlex
import stat

import pytest

from castor.agenda import (
    MARCA, AgendaRecusada, agendar_em, alcanca_no_ambiente_do_cron, comando_de_rotina,
    comando_proprio, listar_de,
)


def _executavel(caminho, conteudo="#!/bin/sh\nexit 0\n"):
    caminho.write_text(conteudo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR)
    return caminho


def _sem_which(_nome):
    raise AssertionError("o which não devia ser consultado quando há pyz")


def test_agendar_acrescenta_linha_marcada():
    tabela = "0 5 * * * outro-comando\n"
    nova = agendar_em(tabela, nome="backup", quando="0 3 * * *",
                      comando="/opt/castor/castor rotina rodar backup")
    assert "outro-comando" in nova, "não pode mexer no que já estava lá"
    assert "0 3 * * *" in nova
    assert MARCA.format(nome="backup") in nova


def test_agendar_de_novo_substitui_a_propria_linha():
    tabela = agendar_em("", nome="backup", quando="0 3 * * *", comando="c1")
    tabela = agendar_em(tabela, nome="backup", quando="0 4 * * *", comando="c2")
    assert tabela.count(MARCA.format(nome="backup")) == 1
    assert "0 4 * * *" in tabela and "0 3 * * *" not in tabela


def test_linha_agendada_e_aceita_pelo_proprio_analisador():
    # A linha vai rodar de madrugada, sem ninguém olhando: se o argparse a
    # recusar, a rotina nunca roda e nada avisa.
    from castor.cli import construir_analisador

    linha = agendar_em("", nome="backup", quando="0 3 * * *",
                       comando="/opt/castor/castor rotina rodar backup --maquina carvalho")
    sem_horario = " ".join(linha.split()[5:]).split("# castor:")[0]
    argumentos = shlex.split(sem_horario)[1:]

    opcoes = construir_analisador().parse_args(argumentos)
    assert opcoes.area == "rotina" and opcoes.verbo == "rodar"


def test_listar_devolve_so_as_rotinas_do_castor():
    tabela = "0 5 * * * alheio\n" + agendar_em("", nome="backup", quando="0 3 * * *", comando="c")
    rotinas = listar_de(tabela)
    assert [r.nome for r in rotinas] == ["backup"]
    assert rotinas[0].quando == "0 3 * * *"


# --- o caminho que o cron vai chamar (#1279) -------------------------------

def test_proprio_prefere_o_wrapper_ao_lado_do_pyz(tmp_path):
    pyz = tmp_path / "castor.pyz"
    pyz.write_text("zip", encoding="utf-8")
    wrapper = _executavel(tmp_path / "castor")

    assert comando_proprio(str(pyz), "/usr/bin/python3", which=_sem_which) == [str(wrapper)]


def test_proprio_sem_wrapper_usa_interpretador_e_pyz_em_caminho_absoluto(tmp_path):
    pyz = tmp_path / "castor.pyz"
    pyz.write_text("zip", encoding="utf-8")

    base = comando_proprio(str(pyz), "/usr/bin/python3", which=_sem_which)

    assert base == ["/usr/bin/python3", str(pyz)]


def test_proprio_wrapper_sem_permissao_de_execucao_nao_serve(tmp_path):
    pyz = tmp_path / "castor.pyz"
    pyz.write_text("zip", encoding="utf-8")
    (tmp_path / "castor").write_text("#!/bin/sh\n", encoding="utf-8")   # sem +x

    assert comando_proprio(str(pyz), "/usr/bin/python3", which=_sem_which) == [
        "/usr/bin/python3", str(pyz)]


def test_proprio_resolve_o_argv0_relativo_contra_o_diretorio_atual(tmp_path, monkeypatch):
    # `python castor.pyz ...` entrega argv[0] = "castor.pyz": relativo, e o
    # cron não roda no diretório de quem agendou.
    (tmp_path / "castor.pyz").write_text("zip", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    base = comando_proprio("castor.pyz", "/usr/bin/python3", which=_sem_which)

    assert base == ["/usr/bin/python3", os.path.join(os.getcwd(), "castor.pyz")]


def test_proprio_nao_resolve_symlink_do_wrapper(tmp_path):
    # O caminho que o usuário instalou é o que fica no crontab.
    real = tmp_path / "real"
    real.mkdir()
    _executavel(real / "castor")
    (real / "castor.pyz").write_text("zip", encoding="utf-8")
    atalho = tmp_path / "atalho"
    atalho.mkdir()
    (atalho / "castor.pyz").symlink_to(real / "castor.pyz")
    _executavel(atalho / "castor")

    assert comando_proprio(str(atalho / "castor.pyz"), "/usr/bin/python3") == [
        str(atalho / "castor")]


def test_proprio_no_checkout_usa_o_which_em_caminho_absoluto():
    base = comando_proprio("/repo/src/castor/__main__.py", "/usr/bin/python3",
                           which=lambda nome: "/opt/bin/castor" if nome == "castor" else None)

    assert base == ["/opt/bin/castor"]


def test_proprio_no_checkout_sem_castor_no_path_devolve_none():
    assert comando_proprio("/repo/src/castor/__main__.py", "/usr/bin/python3",
                           which=lambda nome: None) is None


def test_alcanca_roda_com_o_ambiente_minimo_do_cron():
    chamadas = []

    def executor(argumentos, **opcoes):
        chamadas.append((argumentos, opcoes))
        class Feito:
            returncode, stdout, stderr = 0, "0.4.2\n", ""
        return Feito()

    ok, detalhe = alcanca_no_ambiente_do_cron(["/abs/castor"], "/home/ana", executor=executor)

    assert ok and detalhe == "0.4.2"
    argumentos, opcoes = chamadas[0]
    assert argumentos[:4] == ["env", "-i", "PATH=/usr/bin:/bin", "HOME=/home/ana"]
    assert argumentos[4:6] == ["sh", "-c"] and argumentos[6] == "/abs/castor --versao"
    assert opcoes["cwd"] == "/", "o cron não roda no diretório de quem agendou"


def test_alcanca_distingue_nome_nu_de_caminho_absoluto(tmp_path):
    # Execução de verdade, sem executor falso: o poder do guard é exatamente
    # esta diferença. O programa mora fora de /usr/bin:/bin.
    programa = _executavel(tmp_path / "meu-castor-de-teste")

    com_caminho, _ = alcanca_no_ambiente_do_cron([str(programa)], str(tmp_path))
    nome_nu, _ = alcanca_no_ambiente_do_cron(["meu-castor-de-teste"], str(tmp_path))

    assert com_caminho is True
    assert nome_nu is False


def test_alcanca_recusa_o_que_estoura_o_tempo():
    import subprocess

    def executor(argumentos, **opcoes):
        raise subprocess.TimeoutExpired(argumentos, 30)

    ok, detalhe = alcanca_no_ambiente_do_cron(["/abs/castor"], "/home/ana", executor=executor)

    assert ok is False and "30 s" in detalhe


def test_comando_de_rotina_recusa_quando_o_cron_nao_alcanca(tmp_path):
    pyz = tmp_path / "castor.pyz"
    pyz.write_text("zip", encoding="utf-8")

    with pytest.raises(AgendaRecusada) as recusa:
        comando_de_rotina("backup", "carvalho", argv0=str(pyz), executavel="/usr/bin/python3",
                          casa="/home/ana", verificar=lambda base, casa: (False, "sem python"))

    assert "cron" in str(recusa.value) and "sem python" in str(recusa.value)
    assert "Nada foi gravado" in str(recusa.value)


def test_comando_de_rotina_cita_caminho_com_espaco(tmp_path):
    instalado = tmp_path / "minha pasta"
    instalado.mkdir()
    (instalado / "castor.pyz").write_text("zip", encoding="utf-8")
    wrapper = _executavel(instalado / "castor")

    comando = comando_de_rotina("backup", "carvalho", argv0=str(instalado / "castor.pyz"),
                                executavel="/usr/bin/python3", casa="/home/ana",
                                verificar=lambda base, casa: (True, ""))

    assert shlex.split(comando) == [str(wrapper), "rotina", "rodar", "backup",
                                    "--maquina", "carvalho"]
