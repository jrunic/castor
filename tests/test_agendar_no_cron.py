"""A linha que o `agendar` grava no crontab tem de funcionar no cron.

O cron roda com PATH curto (`/usr/bin:/bin`), sem `~/.local/bin`. O `agendar`
gravava `castor rotina rodar ...` com o nome nu: o cron respondia
`castor: not found`, a saída ia para lugar nenhum e a rotina nunca rodava, sem
erro em lugar nenhum.

Estes testes rodam o `agendar` de verdade (o pyz construído, ou o checkout),
com um `crontab` falso na frente do PATH, e depois **executam a linha gravada**
no ambiente do cron. Teste que só olha o texto da linha passa com qualquer
caminho que pareça absoluto.
"""
import json
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PATH_DO_CRON = "/usr/bin:/bin"


@pytest.fixture(scope="module")
def pyz_construido(tmp_path_factory):
    alvo = tmp_path_factory.mktemp("pacote") / "castor.pyz"
    feito = subprocess.run(
        [sys.executable, "scripts/build-pyz.py", "--saida", str(alvo)],
        capture_output=True, text=True, cwd=RAIZ,
    )
    assert feito.returncode == 0, feito.stderr
    return alvo


def _executavel(caminho: Path, conteudo: str) -> Path:
    caminho.write_text(conteudo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


class Bancada:
    """crontab falso, manifesto e ambiente. O crontab real nunca é alcançado."""

    def __init__(self, tmp_path: Path):
        self.raiz = tmp_path
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        self.tabela = tmp_path / "crontab.txt"
        _executavel(self.bin / "crontab", (
            "#!/bin/sh\n"
            'if [ "$1" = "-l" ]; then cat "$CRONTAB_ARQ" 2>/dev/null; exit 0; fi\n'
            'cat > "$CRONTAB_ARQ"\n'
        ))
        self.manifesto = tmp_path / "castor.json"
        self.manifesto.write_text(json.dumps({
            "maquinas": {"carvalho": {"usuario": "ana", "casa": str(tmp_path),
                                      "sistema": "linux"}},
            "rotinas": {"backup": {"comando": "echo feito", "quando": "0 3 * * *"}},
            "aviso": {"janela_em_minutos": 60},
        }), encoding="utf-8")
        self.path = f"{self.bin}:{PATH_DO_CRON}"
        # Trava de segurança: se o falso não for o primeiro `crontab` do PATH,
        # o teste escreveria no crontab de quem está rodando a suíte.
        assert shutil.which("crontab", path=self.path) == str(self.bin / "crontab")

    def ambiente(self, path: str | None = None) -> dict:
        return {
            "PATH": path or self.path, "HOME": str(self.raiz),
            "CASTOR_CADASTRO": str(self.manifesto), "CASTOR_ESTADO": str(self.raiz),
            "CRONTAB_ARQ": str(self.tabela),
        }

    def agendar_pelo_pyz(self, pyz: Path):
        return subprocess.run(
            [sys.executable, str(pyz), "rotina", "agendar", "backup", "--maquina", "carvalho"],
            capture_output=True, text=True, env=self.ambiente(), cwd=self.raiz,
        )

    def agendar_pelo_checkout(self, path: str | None = None):
        return subprocess.run(
            [sys.executable, "-m", "castor", "rotina", "agendar", "backup",
             "--maquina", "carvalho"],
            capture_output=True, text=True, env=self.ambiente(path), cwd=RAIZ / "src",
        )

    def linha_gravada(self) -> str | None:
        if not self.tabela.exists():
            return None
        achadas = [l for l in self.tabela.read_text(encoding="utf-8").splitlines()
                   if l.rstrip().endswith("# castor:backup")]
        return achadas[0] if achadas else None

    def comando_gravado(self) -> str:
        corpo, _, _ = self.linha_gravada().rpartition("# castor:backup")
        return corpo.split(None, 5)[5].strip()

    def executar_no_ambiente_do_cron(self, comando: str):
        """O que o cron faz: `sh -c` com ambiente mínimo, sem o PATH de quem agendou."""
        return subprocess.run(
            ["env", "-i", f"PATH={PATH_DO_CRON}", f"HOME={self.raiz}",
             f"CASTOR_CADASTRO={self.manifesto}", f"CASTOR_ESTADO={self.raiz}",
             "sh", "-c", comando],
            capture_output=True, text=True, cwd="/",
        )


def test_a_linha_gravada_pelo_pyz_roda_no_ambiente_do_cron(tmp_path, pyz_construido):
    inst = tmp_path / "inst"
    inst.mkdir()
    pyz = shutil.copy(pyz_construido, inst / "castor.pyz")
    bancada = Bancada(tmp_path)

    agendado = bancada.agendar_pelo_pyz(Path(pyz))
    assert agendado.returncode == 0, agendado.stderr

    primeiro = shlex.split(bancada.comando_gravado())[0]
    assert primeiro.startswith("/"), (
        f"o cron não acha '{primeiro}': PATH do cron é {PATH_DO_CRON}")
    rodou = bancada.executar_no_ambiente_do_cron(bancada.comando_gravado())
    assert rodou.returncode == 0, rodou.stdout + rodou.stderr
    assert (tmp_path / "registros" / "backup.log").read_text(encoding="utf-8").strip() == "feito"


def test_com_wrapper_ao_lado_do_pyz_a_linha_usa_o_wrapper(tmp_path, pyz_construido):
    inst = tmp_path / "inst"
    inst.mkdir()
    pyz = shutil.copy(pyz_construido, inst / "castor.pyz")
    # A mesma forma do wrapper que o instalador grava.
    wrapper = _executavel(inst / "castor", (
        f'#!/bin/sh\nexec "{sys.executable}" "$(dirname "$0")/castor.pyz" "$@"\n'))
    bancada = Bancada(tmp_path)

    agendado = bancada.agendar_pelo_pyz(Path(pyz))
    assert agendado.returncode == 0, agendado.stderr

    assert shlex.split(bancada.comando_gravado())[0] == str(wrapper)
    rodou = bancada.executar_no_ambiente_do_cron(bancada.comando_gravado())
    assert rodou.returncode == 0, rodou.stdout + rodou.stderr


def test_recusa_e_nao_grava_quando_o_castor_gravado_nao_roda_no_cron(tmp_path, pyz_construido):
    inst = tmp_path / "inst"
    inst.mkdir()
    pyz = shutil.copy(pyz_construido, inst / "castor.pyz")
    _executavel(inst / "castor", "#!/bin/sh\nexit 1\n")   # wrapper quebrado
    bancada = Bancada(tmp_path)

    agendado = bancada.agendar_pelo_pyz(Path(pyz))

    assert agendado.returncode != 0
    assert bancada.linha_gravada() is None, "gravou uma linha que o cron não consegue rodar"
    assert "cron" in agendado.stderr


def test_do_checkout_sem_castor_no_path_recusa_e_nao_grava(tmp_path):
    bancada = Bancada(tmp_path)

    agendado = bancada.agendar_pelo_checkout()

    assert agendado.returncode != 0
    assert bancada.linha_gravada() is None
    # A mensagem do ramo "não há caminho nenhum": a verificação no ambiente do
    # cron também recusaria o nome nu, e sem esta frase o ramo não se distingue.
    assert "não há 'castor' no PATH" in agendado.stderr


def test_do_checkout_usa_o_castor_do_path_em_caminho_absoluto(tmp_path):
    bancada = Bancada(tmp_path)
    falso = _executavel(bancada.bin / "castor", "#!/bin/sh\necho 0.0-falso\n")

    agendado = bancada.agendar_pelo_checkout()

    assert agendado.returncode == 0, agendado.stderr
    assert shlex.split(bancada.comando_gravado())[0] == str(falso)
