import json
import subprocess
import sys


def executar(tmp_path, *args):
    manifesto = tmp_path / "castor.json"
    manifesto.write_text(json.dumps({
        "maquinas": {"carvalho": {"usuario": "ana", "casa": str(tmp_path), "sistema": "linux"}},
        "rotinas": {
            # Como o material ensina a declarar: UMA string. A fixture antiga
            # usava lista JSON — forma que nenhum manifesto real tem, e era ela
            # que escondia o defeito do comando sem shell.
            "backup": {"comando": "echo feito", "quando": "0 3 * * *"},
            "quebrada": {"comando": "exit 1", "quando": "0 4 * * *"},
        },
        "aviso": {"janela_em_minutos": 60},
    }), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "castor", *args],
        capture_output=True, text=True, cwd="src",
        env={"CASTOR_CADASTRO": str(manifesto), "CASTOR_ESTADO": str(tmp_path),
             "PATH": "/usr/bin:/bin"},
    )


def test_rodar_rotina_declarada_no_manifesto(tmp_path):
    saida = executar(tmp_path, "rotina", "rodar", "backup", "--maquina", "carvalho")
    assert saida.returncode == 0, saida.stderr
    registro = (tmp_path / "registros" / "backup.log").read_text(encoding="utf-8")
    assert registro.strip() == "feito"


def test_falha_propaga_o_codigo_e_registra_a_saida(tmp_path):
    # Sem remetente configurado nada e enviado — e nada e registrado no estado
    # de supressao, de proposito: marcar como avisado o que nunca saiu faria o
    # PRIMEIRO aviso real ser engolido quando o SMTP fosse configurado.
    # A cadeia rotina -> supressor -> estado esta provada em test_rotina.py,
    # onde o remetente e injetavel.
    saida = executar(tmp_path, "rotina", "rodar", "quebrada", "--maquina", "carvalho")
    assert saida.returncode == 1
    assert (tmp_path / "registros" / "quebrada.log").exists()
    assert not (tmp_path / "avisos.json").exists()


def test_sem_configuracao_de_aviso_o_comando_avisa_no_stderr(tmp_path):
    saida = executar(tmp_path, "rotina", "rodar", "quebrada", "--maquina", "carvalho")
    assert "aviso desligado" in saida.stderr


def test_rotina_desconhecida_sai_com_status(tmp_path):
    saida = executar(tmp_path, "rotina", "rodar", "inexistente", "--maquina", "carvalho")
    assert saida.returncode == 1
    assert "inexistente" in saida.stderr
