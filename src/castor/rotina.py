import fcntl
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from castor.correio import Aviso, montar_mensagem


@dataclass(frozen=True)
class Resultado:
    nome: str
    codigo: int
    saida: str
    estourou_o_tempo: bool = False
    nao_rodou_por_trava: bool = False

    @property
    def falhou(self) -> bool:
        return self.codigo != 0


def _texto(fluxo) -> str:
    if fluxo is None:
        return ""
    if isinstance(fluxo, bytes):
        return fluxo.decode("utf-8", "replace")
    return fluxo


def _avisar_se_preciso(resultado, remetente, supressor, de, para, maquina, agora) -> None:
    if not resultado.falhou or remetente is None or supressor is None:
        return
    alarme = f"rotina.{resultado.nome}.falhou"
    if not supressor.pode_avisar(alarme, agora=agora):
        return
    extra = "tempo estourado" if resultado.estourou_o_tempo else f"código {resultado.codigo}"
    mensagem = montar_mensagem(
        Aviso(alarme=alarme, maquina=maquina, assunto_extra=extra, corpo=resultado.saida),
        de=de, para=para,
    )
    try:
        remetente.enviar(mensagem)
    except Exception as erro:
        # O servidor de e-mail fora do ar é o caso comum quando algo falha. Se
        # isto subisse, o cron receberia rastreamento no lugar do código da
        # rotina, e o diagnóstico iria para o castor em vez de ir para o job.
        print(f"[castor] a rotina falhou E o aviso não saiu: {erro}",
              file=sys.stderr)
        return
    # Só registra depois de enviar: falha no envio não deve suprimir o próximo.
    supressor.registrar(alarme, agora=agora)


def rodar(nome: str, comando: list[str], registro: Path, trava: Path,
          teto_em_segundos: int | None = None, remetente=None, supressor=None,
          de: str = "", para: str = "", maquina: str = "", agora: float = 0.0) -> Resultado:
    registro = Path(registro)
    registro.parent.mkdir(parents=True, exist_ok=True)
    trava = Path(trava)
    trava.parent.mkdir(parents=True, exist_ok=True)

    with trava.open("a") as arquivo_da_trava:
        try:
            fcntl.flock(arquivo_da_trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # Já há execução em curso. A seguinte não empilha — desiste.
            return Resultado(nome=nome, codigo=0, saida="", nao_rodou_por_trava=True)

        try:
            # Sob shell, como a ronda (que atravessa o ssh) e a atualização.
            # O manifesto declara UMA string, e sem shell ela vira o nome do
            # programa: '/usr/bin/test 1 -lt 2' virava um caminho inexistente.
            executado = subprocess.run(
                ["sh", "-c", comando], capture_output=True, text=True,
                timeout=teto_em_segundos,
            )
        except subprocess.TimeoutExpired as estouro:
            # Cada stream se normaliza sozinho: um pode vir em bytes e o outro
            # cair no default de texto, e a concatenação misturada explode
            # dentro do próprio tratador.
            parcial = _texto(estouro.stdout) + _texto(estouro.stderr)
            saida = f"{parcial}\n[castor] teto de tempo de {teto_em_segundos}s estourado."
            resultado = Resultado(nome=nome, codigo=124, saida=saida, estourou_o_tempo=True)
        else:
            saida = executado.stdout + executado.stderr
            resultado = Resultado(nome=nome, codigo=executado.returncode, saida=saida)

        with registro.open("a", encoding="utf-8") as arquivo:
            arquivo.write(saida)
        # Saída única: todo caminho de falha passa por aqui, inclusive o teto
        # estourado — que é justamente o que mais precisa avisar.
        _avisar_se_preciso(resultado, remetente, supressor, de, para, maquina, agora)
        return resultado
