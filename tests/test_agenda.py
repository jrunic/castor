import shlex

from castor.agenda import MARCA, agendar_em, listar_de


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
