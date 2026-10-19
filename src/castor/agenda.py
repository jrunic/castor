import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

MARCA = "# castor:{nome}"

# O PATH que o cron entrega ao comando. Fica de fora o `~/.local/bin`, onde o
# instalador põe o `castor`: o nome nu não se resolve ali.
PATH_DO_CRON = "/usr/bin:/bin"


class AgendaRecusada(Exception):
    """O castor não consegue garantir que o cron vai conseguir chamá-lo."""


@dataclass(frozen=True)
class Agendada:
    nome: str
    quando: str
    comando: str


def _e_do_castor(linha: str, nome: str | None = None) -> bool:
    if nome is not None:
        return linha.rstrip().endswith(MARCA.format(nome=nome))
    return "# castor:" in linha


def comando_proprio(argv0: str, executavel: str, which=shutil.which) -> list[str] | None:
    """Os argumentos que levam a ESTE castor por caminho absoluto, ou None.

    O que está rodando agora é a fonte, não o PATH de quem agenda: com dois
    castors instalados, `which` apontaria para o outro. Ordem: o wrapper ao
    lado do pyz em execução (é o que o instalador grava e sobrevive à troca do
    pyz), depois o interpretador mais o pyz, e só no checkout — onde não há
    pyz — o `castor` do PATH. Nada resolve symlink: o caminho que o usuário
    instalou é o que deve ficar no crontab.
    """
    pyz = Path(os.path.abspath(argv0))
    if pyz.suffix == ".pyz":
        wrapper = pyz.with_suffix("")
        if wrapper.is_file() and os.access(wrapper, os.X_OK):
            return [str(wrapper)]
        return [executavel, str(pyz)]
    achado = which("castor")
    return [os.path.abspath(achado)] if achado else None


def alcanca_no_ambiente_do_cron(comando: list[str], casa: str,
                                executor=subprocess.run) -> tuple[bool, str]:
    """Roda `<comando> --versao` com o ambiente que o cron dá (`env -i`, PATH curto).

    É a prova do que o `agendar` vai gravar: a linha só entra no crontab se o
    cron, sozinho, consegue chamá-la. Sem isto o defeito é silencioso — o cron
    descarta a saída e a rotina nunca roda.
    """
    linha = " ".join(shlex.quote(parte) for parte in comando) + " --versao"
    try:
        feito = executor(
            ["env", "-i", f"PATH={PATH_DO_CRON}", f"HOME={casa}", "sh", "-c", linha],
            capture_output=True, text=True, timeout=30, cwd="/",
        )
    except subprocess.TimeoutExpired:
        return False, "passou de 30 s sem responder"
    return feito.returncode == 0, (feito.stdout + feito.stderr).strip()


def comando_de_rotina(nome: str, maquina: str, *, argv0: str, executavel: str, casa: str,
                      which=shutil.which, verificar=alcanca_no_ambiente_do_cron) -> str:
    """O comando que o cron vai executar para a rotina, ou AgendaRecusada."""
    base = comando_proprio(argv0, executavel, which)
    if base is None:
        raise AgendaRecusada(
            "não sei por qual caminho o cron vai me chamar: não estou rodando de um pyz "
            "e não há 'castor' no PATH. Rode pelo castor instalado "
            "(~/.local/bin/castor). Nada foi gravado no crontab.")
    alcancou, detalhe = verificar(base, casa)
    if not alcancou:
        raise AgendaRecusada(
            f"o cron não consegue rodar '{' '.join(base)}' (o PATH do cron é "
            f"{PATH_DO_CRON}): {detalhe or 'sem mensagem'}. Nada foi gravado no crontab.")
    return (" ".join(shlex.quote(parte) for parte in base)
            + f" rotina rodar {shlex.quote(nome)} --maquina {shlex.quote(maquina)}")


def agendar_em(tabela: str, nome: str, quando: str, comando: str) -> str:
    """Devolve a tabela com a rotina posta ou substituída.

    Nunca reescreve linha que não seja do castor: a tabela é do usuário, e
    pode ter entradas que vieram de outro lugar.
    """
    linhas = [l for l in tabela.splitlines() if l.strip() and not _e_do_castor(l, nome)]
    linhas.append(f"{quando} {comando} {MARCA.format(nome=nome)}")
    return "\n".join(linhas) + "\n"


def listar_de(tabela: str) -> list[Agendada]:
    achadas = []
    for linha in tabela.splitlines():
        if not _e_do_castor(linha):
            continue
        corpo, _, marca = linha.rpartition("# castor:")
        campos = corpo.split()
        achadas.append(Agendada(
            nome=marca.strip(),
            quando=" ".join(campos[:5]),
            comando=" ".join(campos[5:]),
        ))
    return achadas
