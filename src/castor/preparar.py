"""O roteiro que leva uma máquina recém-instalada a máquina cliente.

Duas regras estruturais, e as duas existem porque um engano aqui tranca a
máquina do usuário:

1. Todo passo confere o próprio efeito. Um comando que voltou zero afirma sobre
   o processo, não sobre o mundo.
2. Todo passo que fecha um caminho de acesso declara, em 'exige', a prova de
   que o caminho novo funciona. Sem a prova no lugar, o passo não roda.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from castor import conexao as mod_conexao
from castor import medicao as mod_medicao
from castor import rede as mod_rede


class ErroDePreparo(Exception):
    """Base dos erros desta área."""


class PassoNaoProvado(ErroDePreparo):
    pass


class EfeitoNaoConfirmado(ErroDePreparo):
    pass


@dataclass(frozen=True)
class Passo:
    """Um passo do roteiro.

    'conferir' devolve a queixa quando o efeito não apareceu, e nada quando
    apareceu — devolver booleano jogaria fora justamente o que quem lê precisa
    ler ("o relógio está 600 segundos fora", e não "o efeito não apareceu").
    """

    nome: str
    fazer: Callable | None = None
    conferir: Callable | None = None
    exige: tuple[str, ...] = field(default_factory=tuple)
    pendente: str = ""


def executar(passos: list[Passo], contexto: dict, relatar=print) -> list[str]:
    provados: list[str] = []
    for passo in passos:
        if passo.pendente:
            relatar(f"[pendente] {passo.nome}: {passo.pendente}")
            continue
        faltando = [nome for nome in passo.exige if nome not in provados]
        if faltando:
            raise PassoNaoProvado(
                f"o passo '{passo.nome}' fecha um caminho de acesso e exige "
                f"{', '.join(faltando)} — que não foi provado. O roteiro parou "
                f"antes de mexer em qualquer coisa."
            )
        relatar(f"[{passo.nome}] ...")
        if passo.fazer is not None:
            passo.fazer(contexto)
        queixa = passo.conferir(contexto) if passo.conferir is not None else None
        if queixa:
            raise EfeitoNaoConfirmado(
                f"o passo '{passo.nome}' rodou, mas o efeito não apareceu: "
                f"{queixa.rstrip('.')}. O roteiro parou aqui; a máquina continua acessível "
                f"pelo caminho anterior."
            )
        relatar(f"[{passo.nome}] feito")
        provados.append(passo.nome)
    return provados


SUDOERS = "/etc/sudoers.d/castor"
INSTALADOR = ("https://raw.githubusercontent.com/jrunic/castor/main/"
              "scripts/instalar.sh")


def gravar_linha(conteudo: str, arquivo: str, *, acrescentar: bool = False) -> str:
    """Fragmento de shell que grava uma linha inteira, com quebra no fim.

    O fragmento atravessa o ssh e ainda um `sh -c "..."` do outro lado. Por isso
    o formato do printf vai entre aspas SIMPLES: entre duplas, o shell de dentro
    come a barra invertida e o \n vira a letra n — que foi como um sudoers
    inválido nasceu na bancada de 13/09/2026.
    """
    seta = ">>" if acrescentar else ">"
    return f"printf '%s\\n' '{conteudo}' {seta} {arquivo}"


def montar_roteiro(*, nome: str, endereco: str, usuario_inicial: str,
                   usuario_de_servico: str, chave_publica: str,
                   contexto: dict, chave_inicial=None, executor=None,
                   agora=time.time) -> list[Passo]:
    """Os passos, em ordem, do primeiro acesso à máquina pronta.

    O contexto carrega o que um passo mediu para o seguinte usar. O 'executor'
    existe para o teste: por default, cada chamada é uma conexão de verdade, já
    classificada por conexao.conferir.

    Duas coisas que a máquina recém-instalada impõe:

    1. No primeiro acesso não há chave, há senha — o passo zero instala a chave
       numa conexão que repassa o terminal. Dali em diante tudo é por chave, e
       aí a saída pode ser capturada e interpretada. **Em nuvem é o contrário**:
       a imagem nasce com uma chave e sem senha nenhuma, e aí 'chave_inicial'
       diz qual é, o primeiro acesso roda em lote e ninguém digita nada.
    2. sudo sem terminal falha em máquina recém-instalada. Os passos que usam
       sudo pelo usuário inicial vão com terminal repassado, e por isso são um
       só: um pedido de senha, não três. Depois que o sudoers do usuário de
       serviço está de pé e provado, sudo volta a rodar em lote — é por isso que
       o passo de rede EXIGE o de sudo, sem o qual não daria para capturar a URL.
    """
    por_senha = chave_inicial is None
    inicial = mod_conexao.Destino(usuario=usuario_inicial, endereco=endereco,
                                  chave=None if por_senha else Path(chave_inicial))
    # Sempre a chave do castor: é ela que a conferência existe para provar.
    # Conferir com a chave que já funcionava passaria sempre, inclusive quando a
    # instalação da chave nova falhou.
    inicial_com_chave = mod_conexao.Destino(usuario=usuario_inicial,
                                            endereco=endereco,
                                            chave=contexto.get("chave"))
    servico = mod_conexao.Destino(usuario=usuario_de_servico, endereco=endereco,
                                  chave=contexto.get("chave"))

    def correr_de_verdade(destino, comando, **opcoes):
        return mod_conexao.conferir(
            mod_conexao.executar(destino, comando, **opcoes), destino)

    correr = executor or correr_de_verdade

    def abrir_acesso_inicial(_):
        """Única conexão por senha do roteiro — quando há senha a digitar."""
        gravar = gravar_linha(chave_publica, "~/.ssh/authorized_keys",
                              acrescentar=True)
        correr(inicial,
               f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && {gravar} && "
               f"chmod 600 ~/.ssh/authorized_keys",
               com_senha=por_senha)

    def conferir_acesso_inicial(_):
        resposta = correr(inicial_com_chave, "id -un").texto.strip()
        if resposta != usuario_inicial:
            return (f"a chave foi instalada, mas a conexão por chave respondeu "
                    f"'{resposta}' em vez de '{usuario_inicial}'. O acesso por "
                    f"senha continua de pé; nada foi trocado.")
        return None

    def medir(_):
        contexto["medicao"] = mod_medicao.interpretar(
            correr(inicial_com_chave, mod_medicao.SONDA).texto)

    def criar_usuario_de_servico(_):
        """Um sudo só, e sempre com terminal.

        O sudo pode pedir senha mesmo quando o acesso foi por chave — é
        configuração da máquina, não do acesso. Terminal repassado cobre os dois
        casos: onde não pede, nada aparece; onde pede, aparece para quem digita.
        """
        linha = f"{usuario_de_servico} ALL=(ALL) NOPASSWD: ALL"
        casa = f"/home/{usuario_de_servico}"
        autorizadas = f"{casa}/.ssh/authorized_keys"
        correr(inicial, (
            f"sudo sh -c "
            f'"id -u {usuario_de_servico} >/dev/null 2>&1 || '
            f"useradd --create-home --shell /bin/bash {usuario_de_servico}; "
            f"install -d -m 700 -o {usuario_de_servico} -g {usuario_de_servico} "
            f"{casa}/.ssh; "
            f"{gravar_linha(chave_publica, autorizadas, acrescentar=True)}; "
            f"chown {usuario_de_servico}: {autorizadas}; "
            f"chmod 600 {autorizadas}; "
            f"{gravar_linha(linha, SUDOERS)}; "
            f"chmod 440 {SUDOERS}; "
            f'visudo -c -f {SUDOERS}"'), com_terminal=True)

    def conferir_usuario_de_servico(_):
        if correr(inicial_com_chave, f"id -un {usuario_de_servico}").codigo != 0:
            return f"o usuário '{usuario_de_servico}' não existe na máquina."
        return None

    def provar_chave(_):
        """Conexão separada, pelo caminho novo — é esta que autoriza o resto."""
        contexto["prova"] = correr(servico, "id -un").texto.strip()

    def conferir_prova(_):
        if contexto.get("prova") != usuario_de_servico:
            return (f"a conexão como '{usuario_de_servico}' respondeu "
                    f"'{contexto.get('prova')}'. O acesso do usuário inicial "
                    f"continua de pé.")
        return None

    def conferir_sudo(_):
        if correr(servico, "sudo -n true").codigo != 0:
            return (f"'{usuario_de_servico}' não consegue usar sudo sem senha. "
                    f"O arquivo {SUDOERS} não pegou.")
        return None

    def instalar_castor(_):
        correr(servico, f"curl -fsSL {INSTALADOR} | sh")

    def conferir_castor(_):
        if correr(servico, mod_conexao.comando_remoto("--versao")).codigo != 0:
            return "o castor não respondeu depois da instalação."
        return None

    def subir_rede(_):
        """Depois do sudo sem senha, dá para capturar a saída — e a URL."""
        saida = correr(servico, f"sudo {' '.join(mod_rede.montar_subida(nome))}")
        contexto["url_de_login"] = mod_rede.extrair_url_de_login(
            saida.texto + saida.erro)

    return [
        Passo("acesso_inicial", fazer=abrir_acesso_inicial,
              conferir=conferir_acesso_inicial),
        Passo("identidade", fazer=medir, exige=("acesso_inicial",),
              conferir=lambda c: None if c["medicao"].usuario
              else "a máquina não disse quem é o usuário."),
        Passo("relogio", conferir=lambda c: mod_medicao.conferir_relogio(
            c["medicao"], agora=agora())),
        Passo("python", conferir=lambda c: mod_medicao.conferir_python(
            c["medicao"])),
        Passo("usuario_de_servico", fazer=criar_usuario_de_servico,
              conferir=conferir_usuario_de_servico),
        Passo("provar_chave", fazer=provar_chave, conferir=conferir_prova),
        Passo("sudo", exige=("provar_chave",), conferir=conferir_sudo),
        Passo("instalar_castor", fazer=instalar_castor, exige=("provar_chave",),
              conferir=conferir_castor),
        Passo("rede", fazer=subir_rede, exige=("provar_chave", "sudo")),
        Passo("expiracao",
              pendente="conduzida pelo comando, fora do roteiro automático — "
                       "desativar exige o painel, e o castor confere depois"),
        Passo("encerrar_acesso_inicial",
              exige=("provar_chave", "sudo", "instalar_castor"),
              pendente="o acesso do usuário inicial fica de pé na v1: fechá-lo "
                       "mexe na configuração do servidor de SSH e é fatia própria"),
        Passo("aviso",
              pendente="depende do 'castor segredos enviar' em modelo de cofre. "
                       "Até lá, a máquina roda rotina mas não sabe avisar quando "
                       "ela falha."),
    ]
