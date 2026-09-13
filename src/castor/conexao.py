"""A única fronteira de sistema desta área: o binário ssh.

Não há biblioteca de SSH — a política do repositório é stdlib primeiro, e o ssh
do sistema já carrega a configuração que o usuário tem. O valor desta camada é
transformar o código 255 do ssh em um fracasso com nome e providência.
"""
import subprocess
from dataclasses import dataclass
from pathlib import Path

OPCOES_DE_LOTE = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                  "-o", "StrictHostKeyChecking=accept-new")
OPCOES_COM_SENHA = ("-o", "BatchMode=no", "-o", "ConnectTimeout=30",
                    "-o", "StrictHostKeyChecking=accept-new")

SINAIS_DE_REDE = ("could not resolve hostname", "no route to host",
                  "connection timed out", "connection refused",
                  "network is unreachable", "operation timed out")
SINAIS_DE_CHAVE = ("permission denied", "too many authentication failures")

# Onde o instalador de bootstrap põe o comando.
CASA_DO_CASTOR = "$HOME/.local/bin"


class FalhaDeConexao(Exception):
    """Base dos fracassos de conexão."""


class RedeInalcancavel(FalhaDeConexao):
    pass


class ChaveRecusada(FalhaDeConexao):
    pass


class CastorAusente(FalhaDeConexao):
    pass


@dataclass(frozen=True)
class Destino:
    usuario: str
    endereco: str
    chave: Path | None = None
    porta: int = 22

    @property
    def alvo(self) -> str:
        return f"{self.usuario}@{self.endereco}"


@dataclass(frozen=True)
class Saida:
    codigo: int
    texto: str
    erro: str


def montar(destino: Destino, comando: str, *, com_senha: bool = False,
           com_terminal: bool = False) -> list[str]:
    partes = ["ssh"]
    if com_senha or com_terminal:
        partes.append("-t")
    partes += list(OPCOES_COM_SENHA if com_senha else OPCOES_DE_LOTE)
    if destino.chave is not None and not com_senha:
        partes += ["-i", str(destino.chave), "-o", "IdentitiesOnly=yes"]
    if destino.porta != 22:
        partes += ["-p", str(destino.porta)]
    return partes + [destino.alvo, comando]


def executar(destino: Destino, comando: str, *, com_senha: bool = False,
             com_terminal: bool = False, entrada: str | None = None,
             executor=subprocess.run) -> Saida:
    """Dois modos, e a diferença é de propósito.

    Em lote, a saída é capturada e interpretada. Com senha (primeiro acesso) ou
    com terminal (sudo que ainda pede senha), o terminal é repassado para que o
    pedido apareça para quem está digitando — e aí só o código de saída volta.
    Quem precisa do texto não usa estes modos; quem precisa da senha não lê texto.
    """
    if com_senha or com_terminal:
        concluido = executor(montar(destino, comando, com_senha=com_senha,
                                    com_terminal=com_terminal))
        return Saida(codigo=concluido.returncode, texto="", erro="")
    opcoes = {"capture_output": True, "text": True}
    if entrada is not None:
        opcoes["input"] = entrada
    concluido = executor(montar(destino, comando), **opcoes)
    return Saida(codigo=concluido.returncode, texto=concluido.stdout,
                 erro=concluido.stderr)


def conferir(saida: Saida, destino: Destino) -> Saida:
    """255 é fracasso do ssh; qualquer outro código é resposta do comando remoto."""
    if saida.codigo != 255:
        return saida
    erro = saida.erro.lower()
    if any(sinal in erro for sinal in SINAIS_DE_REDE):
        raise RedeInalcancavel(
            f"{destino.endereco} não respondeu. A máquina está ligada e na rede? "
            f"O ssh disse: {saida.erro.strip()}"
        )
    if "host key verification failed" in erro:
        raise ChaveRecusada(
            f"a identidade de {destino.endereco} mudou desde o último acesso. "
            f"Isso acontece quando a máquina foi reinstalada — e também quando "
            f"alguém está no meio do caminho. Confirme antes de apagar a linha "
            f"antiga de ~/.ssh/known_hosts."
        )
    if any(sinal in erro for sinal in SINAIS_DE_CHAVE):
        raise ChaveRecusada(
            f"{destino.alvo} recusou a chave. Rode 'castor chave mostrar' e "
            f"confira se essa chave está no authorized_keys do usuário "
            f"'{destino.usuario}'. O ssh disse: {saida.erro.strip()}"
        )
    raise FalhaDeConexao(f"o ssh falhou com {destino.alvo}: {saida.erro.strip()}")


def comando_remoto(argumentos: str) -> str:
    """Invocação do castor do outro lado, com o PATH corrigido.

    O ssh não-interativo não lê ~/.profile, e é de lá que ~/.local/bin entra no
    PATH. Sem isto, o castor instala com sucesso e toda chamada remota devolve
    127 — como se ele não existisse. Medido em VPS Ubuntu em 13/09/2026.
    """
    return f'PATH="{CASA_DO_CASTOR}:$PATH" castor {argumentos}'


def versao_remota(destino: Destino, *, executor=subprocess.run) -> str:
    saida = conferir(
        executar(destino, comando_remoto("--versao"), executor=executor), destino)
    if saida.codigo == 127 or "not found" in saida.erro.lower():
        raise CastorAusente(
            f"o castor não está instalado em {destino.endereco}. "
            f"Rode 'castor maquina preparar' para instalá-lo."
        )
    if saida.codigo != 0:
        raise FalhaDeConexao(
            f"o castor de {destino.endereco} respondeu com erro: {saida.erro.strip()}"
        )
    return saida.texto.strip()


def gravar_arquivo(caminho: str) -> str:
    """Grava o que vier pela entrada padrão, ao lado, e troca.

    Sem arquivo temporário para alguém ler no meio do caminho, e sem conteúdo em
    argumento — argumento aparece na lista de processos da máquina.
    """
    return (f'umask 077 && mkdir -p "$(dirname {caminho})" && '
            f'cat > {caminho}.novo && mv {caminho}.novo {caminho}')


def somar_arquivo(caminho: str) -> str:
    """A soma do arquivo do outro lado, sem trazer o conteúdo para cá."""
    return (f"sha256sum {caminho} 2>/dev/null || shasum -a 256 {caminho} "
            f"2>/dev/null || true")
