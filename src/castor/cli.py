import argparse
import getpass
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import castor
from castor import atualizacao as mod_atualizacao
from castor import cadastro as mod_cadastro
from castor import configurar as mod_configurar
from castor import chaves as mod_chaves
from castor import cliente as mod_cliente
from castor import cofre as mod_cofre
from castor import conexao as mod_conexao
from castor import medicao as mod_medicao
from castor import preparar as mod_preparar
from castor import rede as mod_rede
from castor import ronda as mod_ronda
from castor import manifesto as mod_manifesto
from castor import segredos as mod_segredos
from castor import unidade as mod_unidade
from castor.manifesto import ErroDeManifesto

AREAS = ("chave", "maquina", "segredos", "servico", "rotina", "ronda",
         "atualizacao")

MANIFESTO_PADRAO = "~/.config/castor/castor.json"


def construir_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="castor",
        description="Toolkit de infra pessoal: chave, máquina, segredos, "
                    "serviço, rotina, ronda e atualização.",
    )
    analisador.add_argument("--versao", action="store_true",
                            help="imprime a versão do castor e sai")
    analisador.add_argument(
        "--cadastro",
        default=None,
        help="caminho do cadastro (default: $CASTOR_CADASTRO ou "
             "XDG cadastro.json / castor.json)",
    )
    areas = analisador.add_subparsers(dest="area", metavar="area")
    areas.add_parser("configurar", help="prepara esta máquina como principal")

    chave = areas.add_parser("chave", help="área chave — o acesso às clientes")
    verbos_chave = chave.add_subparsers(dest="verbo", metavar="verbo",
                                        required=True)

    criar_chave = verbos_chave.add_parser("criar", help="cria o par de chaves")
    criar_chave.add_argument("--caminho", default=None)

    usar_chave = verbos_chave.add_parser("usar", help="adota uma chave existente")
    usar_chave.add_argument("caminho")

    verbos_chave.add_parser("mostrar", help="imprime a chave pública")

    maquina = areas.add_parser("maquina", help="área maquina — as máquinas clientes")
    verbos_maquina = maquina.add_subparsers(dest="verbo", metavar="verbo",
                                            required=True)

    adicionar = verbos_maquina.add_parser(
        "adicionar", help="mede a máquina e a cadastra no manifesto")
    adicionar.add_argument("nome")
    adicionar.add_argument("--endereco", default="")
    adicionar.add_argument("--usuario", default="")
    adicionar.add_argument("--principal", action="store_true",
                           help="cadastra ESTA máquina como principal")
    adicionar.add_argument("--substituir", action="store_true")

    verbos_maquina.add_parser("listar", help="lista as máquinas do manifesto")

    remover = verbos_maquina.add_parser("remover",
                                        help="tira a máquina do manifesto")
    remover.add_argument("nome")

    preparar_maquina = verbos_maquina.add_parser(
        "preparar", help="leva uma máquina recém-instalada a máquina cliente")
    preparar_maquina.add_argument("nome")
    preparar_maquina.add_argument("--endereco", required=True)
    preparar_maquina.add_argument("--usuario-inicial", required=True,
                                  help="o usuário criado na instalação do sistema")
    preparar_maquina.add_argument("--usuario-de-servico", default="castor")
    preparar_maquina.add_argument(
        "--chave-inicial", default=None,
        help="chave que já dá acesso ao usuário inicial — em nuvem, a que a "
             "imagem trouxe. Sem ela, o primeiro acesso é por senha.")

    testar = verbos_maquina.add_parser("testar", help="prova a conexão com a cliente")
    testar.add_argument("nome")

    segredos = areas.add_parser("segredos", help="área segredos")
    verbos = segredos.add_subparsers(dest="verbo", metavar="verbo", required=True)

    gerar = verbos.add_parser("gerar",
                              help="filtra o cofre e grava o arquivo do serviço")
    gerar.add_argument("servico")
    gerar.add_argument("--maquina", required=True)
    gerar.add_argument("--destino", default=None,
                       help="arquivo a gravar; sem ele o comando recusa, "
                            "porque o conteúdo é segredo")

    enviar = verbos.add_parser("enviar",
                               help="entrega o arquivo do serviço à cliente")
    enviar.add_argument("servico")
    enviar.add_argument("--maquina", required=True)

    verbos.add_parser("estado",
                      help="diz, por serviço e máquina, se o que está lá "
                           "corresponde ao que o cofre produziria hoje")

    ver = verbos.add_parser("ver", help="descreve a variável sem imprimir o valor")
    ver.add_argument("arquivo")
    ver.add_argument("variavel")
    ver.add_argument("--revelar", action="store_true",
                     help="imprime o VALOR do segredo na saída padrão")

    rotina = areas.add_parser("rotina", help="área rotina")
    verbos_rotina = rotina.add_subparsers(dest="verbo", metavar="verbo", required=True)

    rodar = verbos_rotina.add_parser("rodar", help="executa a rotina com trava, teto e registro")
    rodar.add_argument("nome")
    rodar.add_argument("--maquina", required=True)

    agendar = verbos_rotina.add_parser("agendar", help="põe a rotina no agendador do sistema")
    agendar.add_argument("nome")
    agendar.add_argument("--maquina", required=True)

    verbos_rotina.add_parser("listar", help="mostra as rotinas do castor no agendador")

    servico = areas.add_parser("servico", help="área servico — o que roda na cliente")
    verbos_servico = servico.add_subparsers(dest="verbo", metavar="verbo",
                                            required=True)

    for nome_do_verbo, ajuda in (
        ("instalar", "entrega o segredo, grava a unit e deixa o serviço ativo"),
        ("remover", "para, desabilita e tira a unit e o segredo"),
        ("reiniciar", "reinicia e confere que voltou"),
    ):
        verbo = verbos_servico.add_parser(nome_do_verbo, help=ajuda)
        verbo.add_argument("servico")
        verbo.add_argument("--maquina", required=True)

    estado_servico = verbos_servico.add_parser(
        "estado", help="diz, por serviço e máquina, se está ativo e habilitado")
    estado_servico.add_argument("--maquina", default=None)

    registro = verbos_servico.add_parser("registro",
                                         help="as últimas linhas do serviço")
    registro.add_argument("servico")
    registro.add_argument("--maquina", required=True)
    registro.add_argument("--linhas", type=int, default=50)

    ronda = areas.add_parser("ronda",
                             help="área ronda — o que você declara vigiar")
    verbos_ronda = ronda.add_subparsers(dest="verbo", metavar="verbo",
                                        required=True)
    rodar_ronda = verbos_ronda.add_parser(
        "rodar", help="roda as checagens declaradas e avisa o que piorou")
    rodar_ronda.add_argument("--ensaio", action="store_true",
                             help="roda tudo e não avisa ninguém")
    verbos_ronda.add_parser(
        "estado", help="mostra o resultado da última ronda, sem reexecutar")

    atualizacao = areas.add_parser(
        "atualizacao", help="área atualizacao — manter as máquinas em dia")
    verbos_atualizacao = atualizacao.add_subparsers(dest="verbo",
                                                    metavar="verbo",
                                                    required=True)
    rodar_atualizacao = verbos_atualizacao.add_parser(
        "rodar", help="atualiza os alvos declarados, e o castor por último")
    rodar_atualizacao.add_argument("--ensaio", action="store_true",
                                    help="mostra o que faria, sem fazer")
    verbos_atualizacao.add_parser(
        "estado", help="que versão está em cada máquina, sem atualizar")

    # Não há mais área sem verbos: as sete listam os próprios.
    return analisador


def _raiz_do_estado() -> Path:
    return Path(os.environ.get("CASTOR_ESTADO", Path.home() / ".local/state/castor"))


def _montar_aviso(opcoes, raiz: Path):
    """Devolve (remetente, supressor, de, para).

    Sem configuração de aviso o comando continua rodando — mas dizendo, em voz
    alta, que ninguém será avisado. Falhar em silêncio aqui é o pior desfecho:
    a rotina roda, quebra, e nada chega.
    """
    from castor.correio import RemetenteSMTP
    from castor.supressao import Supressor

    config = mod_manifesto.ler(Path(opcoes.cadastro)).dados.get("aviso") or {}
    supressor = Supressor(raiz / "avisos.json",
                          janela_em_minutos=config.get("janela_em_minutos", 60))

    campos = ("servidor", "porta", "usuario", "de", "para", "arquivo_de_segredo", "variavel")
    faltando = [c for c in campos if not config.get(c)]
    if faltando:
        print(f"[castor] aviso desligado: falta {', '.join(faltando)} em 'aviso' do "
              f"manifesto. A rotina roda, mas a falha não chega a ninguém.",
              file=sys.stderr)
        return None, supressor, "", ""

    senha = mod_segredos.ver(Path(config["arquivo_de_segredo"]), config["variavel"],
                             revelar=True)
    remetente = RemetenteSMTP(servidor=config["servidor"], porta=int(config["porta"]),
                              usuario=config["usuario"], senha=senha)
    return remetente, supressor, config["de"], config["para"]


def _despachar_rotina(opcoes) -> int:
    from castor import agenda as mod_agenda
    from castor import rotina as mod_rotina

    if opcoes.verbo == "listar":
        tabela = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        for agendada in mod_agenda.listar_de(tabela):
            print(f"{agendada.nome}\t{agendada.quando}")
        return 0

    declarado = mod_manifesto.ler(Path(opcoes.cadastro)).dados.get("rotinas", {})
    if opcoes.nome not in declarado:
        print(f"rotina '{opcoes.nome}' não está declarada no manifesto "
              f"{opcoes.cadastro}.", file=sys.stderr)
        return 1

    if opcoes.verbo == "agendar":
        tabela = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        nova = mod_agenda.agendar_em(
            tabela, nome=opcoes.nome, quando=declarado[opcoes.nome]["quando"],
            comando=f"castor rotina rodar {opcoes.nome} --maquina {opcoes.maquina}",
        )
        subprocess.run(["crontab", "-"], input=nova, text=True, check=True)
        print(f"agendada: {opcoes.nome}")
        return 0

    raiz = _raiz_do_estado()
    remetente, supressor, de, para = _montar_aviso(opcoes, raiz)
    resultado = mod_rotina.rodar(
        opcoes.nome, declarado[opcoes.nome]["comando"],
        registro=raiz / "registros" / f"{opcoes.nome}.log",
        trava=raiz / "travas" / f"{opcoes.nome}.trava",
        teto_em_segundos=declarado[opcoes.nome].get("teto_em_segundos"),
        remetente=remetente, supressor=supressor, de=de, para=para,
        maquina=opcoes.maquina, agora=time.time(),
    )
    return resultado.codigo


def _cofre_de(lido) -> dict:
    declarado = lido.dados.get("cofre")
    if declarado is None:
        raise mod_cofre.CofreAusente(
            f"o manifesto {lido.origem} não declara onde fica o cofre. "
            f"Acrescente a chave 'cofre' com o caminho do arquivo."
        )
    return mod_cofre.ler(Path(declarado))


def _gravar_na_cliente(destino_ssh, caminho: str, conteudo: str) -> None:
    """Erro nomeia o arquivo, nunca o conteúdo."""
    saida = mod_conexao.conferir(
        mod_conexao.executar(destino_ssh, mod_conexao.gravar_arquivo(caminho),
                             entrada=conteudo), destino_ssh)
    if saida.codigo != 0:
        raise mod_conexao.FalhaDeConexao(
            f"não consegui gravar {caminho} na máquina: {saida.erro.strip()}")


def _entregar(lido, servico: str, maquina: str, destino_ssh) -> str:
    """As duas gravações que toda entrega faz. Devolve o arquivo do serviço.

    Extraída porque o `preparar` entrega o aviso pelo mesmo caminho — e caminho
    de entrega duplicado é onde um dos dois deixa de mandar o manifesto.
    """
    conteudo = mod_segredos.montar(lido, servico, maquina, _cofre_de(lido))
    arquivo = mod_segredos.destino_de(lido, servico, maquina)
    _gravar_na_cliente(destino_ssh, arquivo, conteudo)
    _gravar_na_cliente(destino_ssh, mod_cliente.destino_na_cliente(lido, maquina),
                       mod_cliente.como_texto(lido, maquina))
    return arquivo


def _enviar_servico(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    destino_ssh = _destino_de(opcoes, opcoes.maquina)
    arquivo = _entregar(lido, opcoes.servico, opcoes.maquina, destino_ssh)
    print(f"entregue em {opcoes.maquina}: {arquivo} e o manifesto da máquina")
    return 0


def _estado_dos_segredos(opcoes) -> int:
    """Afirma sobre o ARQUIVO, não sobre o processo que o consome."""
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    valores = _cofre_de(lido)
    pendencias = 0
    for servico, declarado in sorted(lido.dados.get("servicos", {}).items()):
        alvos = declarado.get("maquinas") or [
            nome for nome in lido.nomes() if not lido.maquina(nome).e_principal]
        for maquina in alvos:
            arquivo = mod_segredos.destino_de(lido, servico, maquina)
            esperada = mod_segredos.soma(
                mod_segredos.montar(lido, servico, maquina, valores))
            try:
                destino_ssh = _destino_de(opcoes, maquina)
                saida = mod_conexao.conferir(
                    mod_conexao.executar(destino_ssh,
                                         mod_conexao.somar_arquivo(arquivo)),
                    destino_ssh)
                partes = saida.texto.split()
                # Só conta como soma o que TEM cara de soma. Sem isto, qualquer
                # ruído da máquina viraria "desatualizado" em vez de "ausente",
                # e quem lê procuraria a diferença num arquivo que não existe.
                obtida = partes[0] if partes and len(partes[0]) == 64 and all(
                    letra in "0123456789abcdef" for letra in partes[0]) else ""
            except (mod_conexao.FalhaDeConexao, ErroDeManifesto) as erro:
                print(f"{servico}\t{maquina}\tinalcançável\t{erro}")
                pendencias += 1
                continue
            if not obtida:
                print(f"{servico}\t{maquina}\tausente\t{arquivo}")
                pendencias += 1
            elif obtida == esperada:
                print(f"{servico}\t{maquina}\tem dia\t{esperada[:12]}")
            else:
                print(f"{servico}\t{maquina}\tdesatualizado\t"
                      f"esperado {esperada[:12]}, lá {obtida[:12]}")
                pendencias += 1
    return 8 if pendencias else 0


CODIGO_DE_SERVICO = 9


class ServicoNaoObedeceu(Exception):
    """Comando de serviço que devia mudar o mundo e voltou com erro."""


def _so_linux(lido, maquina: str) -> None:
    sistema = lido.maquina(maquina).sistema
    if sistema != "linux":
        raise ErroDeManifesto(
            f"'{maquina}' é {sistema}, e serviço é Linux nesta versão. Quem "
            f"roda serviço é a máquina cliente."
        )


def _mandar(destino_ssh, argumentos: str) -> None:
    """Comando que MUDA alguma coisa. Erro aqui para o resto.

    Sem isto, um daemon-reload que falha só apareceria lá na frente, no
    is-active — longe da causa.
    """
    saida = mod_conexao.executar(destino_ssh,
                                 mod_conexao.comando_de_servico(argumentos))
    if saida.codigo != 0:
        raise ServicoNaoObedeceu(
            f"'systemctl --user {argumentos}' falhou: {saida.erro.strip()}")


def _perguntar(destino_ssh, argumentos: str) -> str:
    """Comando que PERGUNTA. Código diferente de zero é resposta, não erro:
    'is-active' de serviço parado sai 3 com 'inactive' na saída padrão."""
    return mod_conexao.executar(
        destino_ssh, mod_conexao.comando_de_servico(argumentos)).texto.strip()


def _instalar_servico(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    _so_linux(lido, opcoes.maquina)
    maquina = lido.maquina(opcoes.maquina)
    declarado = lido.dados.get("servicos", {}).get(opcoes.servico)
    if declarado is None:
        raise ErroDeManifesto(
            f"serviço '{opcoes.servico}' não está em 'servicos' de {lido.origem}.")
    texto = mod_unidade.montar(opcoes.servico, declarado, casa=maquina.casa,
                               casa_principal=lido.principal().casa)
    destino_ssh = _destino_de(opcoes, opcoes.maquina)

    # 1. o segredo primeiro: sem EnvironmentFile o systemd recusa a unit, e o
    #    erro apareceria longe da causa.
    _entregar(lido, opcoes.servico, opcoes.maquina, destino_ssh)
    # 2. a unit
    _gravar_na_cliente(destino_ssh,
                       mod_unidade.caminho(maquina.casa, opcoes.servico), texto)
    # 3. o linger, que é o que faz o serviço sobreviver ao fim da sessão
    mod_conexao.executar(destino_ssh,
                         f"sudo loginctl enable-linger {maquina.usuario}")
    if "Linger=yes" not in mod_conexao.executar(
            destino_ssh, f"loginctl show-user {maquina.usuario}").texto:
        print(f"o linger de '{maquina.usuario}' não ficou ligado. Sem ele o "
              f"serviço morre quando a última sessão fechar — não vou dizer "
              f"que instalei.", file=sys.stderr)
        return CODIGO_DE_SERVICO
    # 4. recarregar e ligar — os dois mudam o mundo, e falha aqui para tudo
    _mandar(destino_ssh, "daemon-reload")
    _mandar(destino_ssh, f"enable --now {opcoes.servico}.service")

    situacao = _perguntar(destino_ssh, f"is-active {opcoes.servico}.service")
    if situacao != "active":
        print(f"o serviço '{opcoes.servico}' ficou '{situacao}' em "
              f"{opcoes.maquina}. Veja o que ele disse: 'castor servico "
              f"registro {opcoes.servico} --maquina {opcoes.maquina}'.",
              file=sys.stderr)
        return CODIGO_DE_SERVICO
    print(f"'{opcoes.servico}' está ativo em {opcoes.maquina}, e continua "
          f"depois que esta sessão fechar.")
    return 0


def _remover_servico(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    _so_linux(lido, opcoes.maquina)
    maquina = lido.maquina(opcoes.maquina)
    destino_ssh = _destino_de(opcoes, opcoes.maquina)

    _mandar(destino_ssh, f"disable --now {opcoes.servico}.service")
    # Único comando destrutivo que o castor manda para a cliente, e ele apaga
    # dois caminhos que o próprio castor escreveu, calculados do manifesto.
    arquivo = mod_segredos.destino_de(lido, opcoes.servico, opcoes.maquina)
    unit = mod_unidade.caminho(maquina.casa, opcoes.servico)
    mod_conexao.executar(destino_ssh, f"rm -f {unit} {arquivo}")
    _mandar(destino_ssh, "daemon-reload")

    situacao = _perguntar(destino_ssh, f"is-active {opcoes.servico}.service")
    if situacao == "active":
        print(f"'{opcoes.servico}' continua ativo em {opcoes.maquina}.",
              file=sys.stderr)
        return CODIGO_DE_SERVICO
    habilitado = _perguntar(destino_ssh, f"is-enabled {opcoes.servico}.service")
    if habilitado == "enabled":
        print(f"'{opcoes.servico}' parou mas continua habilitado em "
              f"{opcoes.maquina} — voltaria no próximo boot.", file=sys.stderr)
        return CODIGO_DE_SERVICO

    print(f"'{opcoes.servico}' saiu de {opcoes.maquina}: unit e segredo "
          f"removidos. O linger do usuário fica ligado, porque pode estar "
          f"sustentando outro serviço.")
    return 0


def _servicos_com_comando(lido) -> list:
    return [(nome, declarado)
            for nome, declarado in sorted(lido.dados.get("servicos", {}).items())
            if declarado.get("comando")]


def _estado_dos_servicos(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    caidos = 0
    for nome, declarado in _servicos_com_comando(lido):
        alvos = declarado.get("maquinas") or [
            m for m in lido.nomes() if not lido.maquina(m).e_principal]
        for maquina in alvos:
            if opcoes.maquina and maquina != opcoes.maquina:
                continue
            sistema = lido.maquina(maquina).sistema
            if sistema != "linux":
                # Pular em silêncio faria o relatório parecer completo.
                print(f"{nome}\t{maquina}\tpulada\t{sistema}, e serviço é Linux")
                continue
            try:
                destino_ssh = _destino_de(opcoes, maquina)
                situacao = _perguntar(destino_ssh, f"is-active {nome}.service")
                habilitado = _perguntar(destino_ssh, f"is-enabled {nome}.service")
            except (mod_conexao.FalhaDeConexao, ErroDeManifesto) as erro:
                print(f"{nome}\t{maquina}\tinalcançável\t{erro}")
                caidos += 1
                continue
            print(f"{nome}\t{maquina}\t{situacao}\t{habilitado}")
            if situacao != "active":
                caidos += 1
    return CODIGO_DE_SERVICO if caidos else 0


def _reiniciar_servico(opcoes) -> int:
    """É por aqui que um segredo trocado chega ao processo que o consome."""
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    _so_linux(lido, opcoes.maquina)
    destino_ssh = _destino_de(opcoes, opcoes.maquina)
    _mandar(destino_ssh, f"restart {opcoes.servico}.service")
    situacao = _perguntar(destino_ssh, f"is-active {opcoes.servico}.service")
    if situacao != "active":
        print(f"'{opcoes.servico}' não voltou: está '{situacao}'. Veja "
              f"'castor servico registro {opcoes.servico} --maquina "
              f"{opcoes.maquina}'.", file=sys.stderr)
        return CODIGO_DE_SERVICO
    print(f"'{opcoes.servico}' reiniciado e ativo em {opcoes.maquina}.")
    return 0


def _registro_do_servico(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    _so_linux(lido, opcoes.maquina)
    destino_ssh = _destino_de(opcoes, opcoes.maquina)
    saida = mod_conexao.executar(
        destino_ssh, mod_conexao.comando_de_registro(opcoes.servico,
                                                     opcoes.linhas))
    print(saida.texto, end="")
    return 0


def _despachar_servico(opcoes) -> int:
    if opcoes.verbo == "instalar":
        return _instalar_servico(opcoes)
    if opcoes.verbo == "remover":
        return _remover_servico(opcoes)
    if opcoes.verbo == "reiniciar":
        return _reiniciar_servico(opcoes)
    if opcoes.verbo == "registro":
        return _registro_do_servico(opcoes)
    return _estado_dos_servicos(opcoes)


CODIGO_DE_RONDA = 10


def _aviso_da_principal(opcoes, raiz):
    """O remetente da ronda, com a senha vinda do COFRE.

    Na cliente, a senha sai do arquivo de serviço que o castor entregou. Aqui na
    principal esse arquivo não existe — o que existe é o cofre, que é de onde
    aquele arquivo teria saído.
    """
    from castor.correio import RemetenteSMTP
    from castor.supressao import Supressor

    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    config = lido.dados.get("aviso") or {}
    supressor = Supressor(raiz / "avisos.json",
                          janela_em_minutos=config.get("janela_em_minutos", 60))

    campos = ("servidor", "porta", "usuario", "de", "para", "variavel")
    faltando = [campo for campo in campos if not config.get(campo)]
    if faltando:
        print(f"[castor] aviso desligado: falta {', '.join(faltando)} em "
              f"'aviso' do manifesto. A ronda roda, mas o que ela achar não "
              f"chega a ninguém.", file=sys.stderr)
        return None, supressor, "", ""

    senha = _cofre_de(lido).get(config["variavel"])
    if senha is None:
        print(f"[castor] aviso desligado: o cofre não tem "
              f"{config['variavel']}.", file=sys.stderr)
        return None, supressor, "", ""

    remetente = RemetenteSMTP(servidor=config["servidor"],
                              porta=int(config["porta"]),
                              usuario=config["usuario"], senha=senha)
    return remetente, supressor, config["de"], config["para"]


def _enviar_com_cuidado(remetente, mensagem) -> bool:
    try:
        remetente.enviar(mensagem)
        return True
    except Exception as erro:
        print(f"[castor] a ronda terminou, mas o aviso não saiu: {erro}",
              file=sys.stderr)
        return False


def _avisar_da_ronda(opcoes, raiz, resultados, pioraram, melhoraram) -> None:
    """Avisa o que MUDOU de estado — não o que continua mal."""
    from castor.correio import Aviso, montar_mensagem

    if not pioraram and not melhoraram:
        return
    remetente, supressor, de, para = _aviso_da_principal(opcoes, raiz)
    if remetente is None:
        return

    por_nome = {r.nome: r for r in resultados}
    agora = time.time()
    for nome in pioraram:
        alarme = f"ronda.{nome}.falhou"
        if not supressor.pode_avisar(alarme, agora=agora):
            continue
        aviso = Aviso(alarme=alarme, maquina=nome, assunto_extra="ronda",
                      corpo=por_nome[nome].detalhe)
        if _enviar_com_cuidado(remetente,
                               montar_mensagem(aviso, de=de, para=para)):
            supressor.registrar(alarme, agora=agora)
    for nome in melhoraram:
        aviso = Aviso(alarme=f"ronda.{nome}.voltou", maquina=nome,
                      assunto_extra="ronda: voltou ao normal", corpo="")
        _enviar_com_cuidado(remetente, montar_mensagem(aviso, de=de, para=para))
        # Esquece o alarme de falha: se ela voltar dentro da janela, avisa de
        # novo. Silêncio depois de um "voltou ao normal" lê-se como "está bem".
        supressor.esquecer(f"ronda.{nome}.falhou")


def _checar_uma(opcoes, nome: str, declarada: dict, tipo: str):
    maquina = declarada["maquina"]
    if tipo == "expiracao":
        # A única que roda AQUI: um nó não lê a própria expiração.
        tailscale = _binario_do_tailscale()
        if tailscale is None:
            return mod_ronda.Resultado(
                nome=f"expiracao:{maquina}", passou=False,
                detalhe="não achei o comando 'tailscale' nesta máquina")
        try:
            expiracao = mod_rede.expiracao_de(_status_da_rede(tailscale), maquina)
        except (mod_rede.ErroDeRede, ValueError) as erro:
            return mod_ronda.Resultado(nome=f"expiracao:{maquina}", passou=False,
                                       detalhe=str(erro))
        return mod_ronda.avaliar_expiracao(maquina, expiracao)

    destino_ssh = _destino_de(opcoes, maquina)
    if tipo == "servico":
        situacao = _perguntar(destino_ssh,
                              f"is-active {declarada['servico']}.service")
        return mod_ronda.avaliar_servico(nome, situacao)

    saida = mod_conexao.conferir(
        mod_conexao.executar(destino_ssh, declarada["comando"]), destino_ssh)
    return mod_ronda.avaliar_comando(nome, saida.codigo, saida.texto + saida.erro)


def _rodar_ronda(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    declaradas = lido.dados.get("ronda", {}).get("checagens", {})
    # Confere TODAS antes de rodar QUALQUER uma: declaração torta descoberta no
    # meio deixaria metade das checagens rodadas e metade não.
    tipos = {nome: mod_ronda.conferir_declaracao(nome, declarada)
             for nome, declarada in sorted(declaradas.items())}

    # A expiração roda AQUI, na principal — máquina fora do ar não a impede, e é
    # justamente quando a máquina some que saber da expiração importa.
    resultados = [_checar_uma(opcoes, nome, declarada, "expiracao")
                  for nome, declarada in sorted(declaradas.items())
                  if tipos[nome] == "expiracao"]

    # Agrupadas por máquina: é o que faz "máquina fora do ar é UMA falha" ser
    # evidente no laço, em vez de depender de limpeza depois do fato.
    por_maquina = {}
    for nome, declarada in sorted(declaradas.items()):
        if tipos[nome] != "expiracao":
            por_maquina.setdefault(declarada["maquina"], []).append(
                (nome, declarada))

    for maquina, checagens in sorted(por_maquina.items()):
        for nome, declarada in checagens:
            try:
                resultados.append(
                    _checar_uma(opcoes, nome, declarada, tipos[nome]))
            except mod_conexao.FalhaDeConexao as erro:
                resultados.extend(mod_ronda.maquina_inalcancavel(
                    maquina, dict(checagens), str(erro)))
                break

    for resultado in resultados:
        print(f"{resultado.nome}\t{'passou' if resultado.passou else 'falhou'}"
              f"\t{resultado.detalhe}")

    if opcoes.ensaio:
        # Não grava: o arquivo é a linha de base da comparação, e sobrescrevê-lo
        # faria a falha em curso deixar de ser avisada na ronda seguinte.
        print("[ensaio] nada foi avisado e nada foi gravado.")
        return CODIGO_DE_RONDA if any(not r.passou for r in resultados) else 0

    raiz = _raiz_do_estado()
    arquivo = raiz / "ronda.json"
    anterior = mod_ronda.ultima(arquivo)
    guardados = anterior["resultados"] if anterior else None
    pioraram = mod_ronda.piorou(guardados, resultados)
    melhoraram = mod_ronda.melhorou(guardados, resultados)
    mod_ronda.gravar(arquivo, resultados, agora=time.time())
    _avisar_da_ronda(opcoes, raiz, resultados, pioraram, melhoraram)
    return CODIGO_DE_RONDA if any(not r.passou for r in resultados) else 0


def _estado_da_ronda(opcoes) -> int:
    guardado = mod_ronda.ultima(_raiz_do_estado() / "ronda.json")
    if guardado is None:
        print("nenhuma ronda rodou nesta máquina ainda. Rode "
              "'castor ronda rodar'.", file=sys.stderr)
        return 1
    quando = time.strftime("%Y-%m-%d %H:%M %z",
                           time.localtime(guardado["quando"]))
    idade = int((time.time() - guardado["quando"]) // 3600)
    print(f"última ronda: {quando} ({idade}h atrás)")
    for resultado in guardado["resultados"]:
        print(f"{resultado['nome']}\t"
              f"{'passou' if resultado['passou'] else 'falhou'}\t"
              f"{resultado['detalhe']}")
    return CODIGO_DE_RONDA if any(
        not r["passou"] for r in guardado["resultados"]) else 0


CODIGO_DE_ATUALIZACAO = 11


def _aqui(comando: str) -> tuple[str, str]:
    """Roda na própria máquina. A principal não tem ssh de volta para si.

    Devolve (saída, erro): quem falha explica no erro padrão, e descartar isso
    deixa quem lê com o sintoma sem a causa.
    """
    concluido = subprocess.run(["sh", "-c", comando], capture_output=True,
                               text=True)
    return concluido.stdout.strip(), concluido.stderr.strip()


def _versao_em(destino_ssh, nome: str, declarado: dict) -> str:
    return mod_conexao.executar(
        destino_ssh,
        mod_atualizacao.comando_de_versao(nome, declarado)).texto.strip()


def _alvos_por_maquina(lido) -> list:
    """Os alvos na ordem de execução: o castor por último, sempre.

    E a principal por último de tudo — o processo em execução continua com o
    código velho em memória, e o relatório precisa ter saído antes.
    """
    declarados = lido.dados.get("atualizacao", {}).get("alvos", {})
    pares = []
    for nome, declarado in sorted(declarados.items()):
        for maquina in declarado.get("maquinas", []):
            pares.append((maquina, nome, declarado))
    return sorted(pares, key=lambda par: (par[2].get("tipo") == "castor",
                                          lido.maquina(par[0]).e_principal))


def _atualizar_um(opcoes, lido, maquina, nome, declarado) -> tuple:
    if lido.maquina(maquina).e_principal:
        # Sem ssh: o _destino_de recusa a principal, e com razão.
        destino_ssh = None
        antes, _ = _aqui(mod_atualizacao.comando_de_versao(nome, declarado))
        _, queixa = _aqui(mod_atualizacao.comando_de(declarado))
        depois, _ = _aqui(mod_atualizacao.comando_de_versao(nome, declarado))
    else:
        destino_ssh = _destino_de(opcoes, maquina)
        antes = _versao_em(destino_ssh, nome, declarado)
        saida = mod_conexao.conferir(
            mod_conexao.executar(destino_ssh,
                                 mod_atualizacao.comando_de(declarado)),
            destino_ssh)
        queixa = saida.erro.strip()
        depois = _versao_em(destino_ssh, nome, declarado)

    situacao, passou = mod_atualizacao.concluir(nome, antes, depois)
    if not passou and queixa:
        # O sintoma sem a causa manda quem lê procurar no escuro.
        situacao = f"{situacao} — a máquina disse: {queixa.splitlines()[-1]}"

    servico = declarado.get("reiniciar")
    if passou and servico and antes.strip() != depois.strip():
        if destino_ssh is None:
            return (f"{situacao}; reiniciar '{servico}' na principal não é "
                    f"desta versão", passou)
        _mandar(destino_ssh, f"restart {servico}.service")
        if _perguntar(destino_ssh, f"is-active {servico}.service") != "active":
            return (f"{situacao}, mas '{servico}' não voltou", False)
        situacao = f"{situacao}, '{servico}' reiniciado"
    return (situacao, passou)


def _rodar_atualizacao(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    problemas = 0
    caidas = set()
    for maquina, nome, declarado in _alvos_por_maquina(lido):
        if opcoes.ensaio:
            print(f"[ensaio] {maquina}\t{nome}\t"
                  f"{mod_atualizacao.comando_de(declarado)}")
            continue
        if maquina in caidas:
            print(f"{maquina}\t{nome}\tpulado\tmáquina inalcançável")
            continue
        try:
            situacao, passou = _atualizar_um(opcoes, lido, maquina, nome,
                                             declarado)
        except mod_conexao.FalhaDeConexao as erro:
            caidas.add(maquina)
            print(f"{maquina}\t{nome}\tinalcançável\t{erro}")
            problemas += 1
            continue
        print(f"{maquina}\t{nome}\t{'ok' if passou else 'falhou'}\t{situacao}")
        if not passou:
            problemas += 1
    return CODIGO_DE_ATUALIZACAO if problemas else 0


def _estado_da_atualizacao(opcoes) -> int:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    ausentes = 0
    for maquina, nome, declarado in _alvos_por_maquina(lido):
        try:
            if lido.maquina(maquina).e_principal:
                versao, _ = _aqui(mod_atualizacao.comando_de_versao(nome,
                                                                    declarado))
            else:
                versao = _versao_em(_destino_de(opcoes, maquina), nome,
                                    declarado)
        except (mod_conexao.FalhaDeConexao, ErroDeManifesto) as erro:
            print(f"{maquina}\t{nome}\tinalcançável\t{erro}")
            ausentes += 1
            continue
        if not versao:
            print(f"{maquina}\t{nome}\tausente")
            ausentes += 1
        else:
            print(f"{maquina}\t{nome}\t{versao}")
    return CODIGO_DE_ATUALIZACAO if ausentes else 0


def _despachar_atualizacao(opcoes) -> int:
    if opcoes.verbo == "rodar":
        return _rodar_atualizacao(opcoes)
    return _estado_da_atualizacao(opcoes)


def _despachar_ronda(opcoes) -> int:
    if opcoes.verbo == "rodar":
        return _rodar_ronda(opcoes)
    return _estado_da_ronda(opcoes)


def _despachar_segredos(opcoes) -> int:
    if opcoes.verbo == "estado":
        return _estado_dos_segredos(opcoes)
    if opcoes.verbo == "enviar":
        try:
            return _enviar_servico(opcoes)
        except mod_conexao.FalhaDeConexao as erro:
            print(str(erro), file=sys.stderr)
            return CODIGOS.get(type(erro), 5)
    if opcoes.verbo == "gerar":
        if not opcoes.destino:
            print("falta --destino. O conteúdo é segredo e não vai para a "
                  "saída padrão.", file=sys.stderr)
            return 1
        lido = mod_manifesto.ler(Path(opcoes.cadastro))
        conteudo = mod_segredos.montar(lido, opcoes.servico, opcoes.maquina,
                                       _cofre_de(lido))
        destino = Path(opcoes.destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.touch(mode=0o600, exist_ok=True)
        destino.chmod(0o600)
        destino.write_text(conteudo, encoding="utf-8")
        print(f"gravado: {destino}")
        return 0
    print(mod_segredos.ver(Path(opcoes.arquivo), opcoes.variavel, revelar=opcoes.revelar))
    return 0


def _caminho_da_chave(opcoes) -> Path:
    declarado = mod_manifesto.ler_ou_vazio(Path(opcoes.cadastro)).caminho_da_chave()
    return declarado or mod_chaves.caminho_padrao()


def _anotar_chave(opcoes, privada: Path) -> None:
    lido = mod_manifesto.ler_ou_vazio(Path(opcoes.cadastro))
    mod_manifesto.gravar(mod_manifesto.anotar(lido, "chave", str(privada)))


def _despachar_chave(opcoes) -> int:
    if opcoes.verbo == "criar":
        caminho = (Path(opcoes.caminho).expanduser() if opcoes.caminho
                   else mod_chaves.caminho_padrao())
        privada = mod_chaves.criar(caminho)
        _anotar_chave(opcoes, privada)
        print(f"criada: {privada}")
        print(mod_chaves.mostrar(privada))
        return 0
    if opcoes.verbo == "usar":
        privada = mod_chaves.adotar(Path(opcoes.caminho))
        _anotar_chave(opcoes, privada)
        print(f"adotada: {privada}")
        return 0
    print(mod_chaves.mostrar(_caminho_da_chave(opcoes)))
    return 0


CODIGOS = {
    mod_conexao.RedeInalcancavel: 2,
    mod_conexao.ChaveRecusada: 3,
    mod_conexao.CastorAusente: 4,
}


def _destino_de(opcoes, nome: str) -> mod_conexao.Destino:
    lido = mod_manifesto.ler(Path(opcoes.cadastro))
    maquina = lido.maquina(nome)
    if maquina.e_principal:
        raise ErroDeManifesto(
            f"'{nome}' é a máquina principal — ela não é acessada, ela acessa. "
            f"Rode este comando contra uma cliente."
        )
    if not maquina.endereco:
        raise ErroDeManifesto(
            f"a máquina '{nome}' não tem endereço no manifesto. Rode "
            f"'castor maquina adicionar {nome} --endereco <endereço> --substituir'."
        )
    return mod_conexao.Destino(usuario=maquina.usuario, endereco=maquina.endereco,
                               chave=lido.caminho_da_chave())


def _medir_aqui() -> mod_medicao.Medicao:
    return mod_medicao.Medicao(
        usuario=getpass.getuser(), casa=str(Path.home()),
        sistema=platform.system().lower(), epoca=int(time.time()),
        fuso=time.strftime("%z"), python=platform.python_version(), sudo=False,
    )


def _medir_la(destino: mod_conexao.Destino) -> mod_medicao.Medicao:
    saida = mod_conexao.conferir(
        mod_conexao.executar(destino, mod_medicao.SONDA), destino)
    return mod_medicao.interpretar(saida.texto)


def _adicionar_maquina(opcoes) -> int:
    lido = mod_manifesto.ler_ou_vazio(Path(opcoes.cadastro))
    if opcoes.principal:
        medido = _medir_aqui()
        endereco = ""
    else:
        if not opcoes.endereco:
            print("uma máquina cliente precisa de --endereco.", file=sys.stderr)
            return 1
        endereco = opcoes.endereco
        destino = mod_conexao.Destino(
            usuario=opcoes.usuario or getpass.getuser(), endereco=endereco,
            chave=lido.caminho_da_chave())
        try:
            medido = _medir_la(destino)
        except mod_conexao.FalhaDeConexao as erro:
            print(str(erro), file=sys.stderr)
            return CODIGOS.get(type(erro), 5)
        except mod_medicao.MedicaoIncompleta as erro:
            print(str(erro), file=sys.stderr)
            return 7

    for queixa in (mod_medicao.conferir_relogio(medido, agora=time.time()),
                   mod_medicao.conferir_python(medido)):
        if queixa:
            print(f"[castor] {queixa}", file=sys.stderr)

    maquina = mod_manifesto.Maquina(
        nome=opcoes.nome, usuario=medido.usuario, casa=medido.casa,
        sistema=medido.sistema, endereco=endereco, python=medido.python,
        papel="principal" if opcoes.principal else "cliente")
    mod_manifesto.gravar(
        mod_manifesto.acrescentar(lido, maquina, substituir=opcoes.substituir))
    print(f"cadastrada: {maquina.nome} ({maquina.papel}, {maquina.sistema}, "
          f"casa {maquina.casa})")
    return 0


def _binario_do_tailscale() -> str | None:
    return mod_rede.achar_binario(which=shutil.which)


def _status_da_rede(binario: str) -> str:
    return subprocess.run([binario, "status", "--json"],
                          capture_output=True, text=True).stdout


def _aguardar(mensagem: str) -> None:
    try:
        input(mensagem)
    except EOFError:
        pass


def _conduzir_expiracao(nome: str) -> int:
    """O castor instrui e confere; desativar é do painel, por desenho do tailscale.

    A conferência roda AQUI, na principal: um nó não enxerga a própria expiração
    de chave — ela só aparece na entrada de peer que as outras máquinas veem.
    """
    tailscale = _binario_do_tailscale()
    if tailscale is None:
        print("não achei o comando 'tailscale' nesta máquina, então não tenho "
              "como conferir a expiração da chave de nó dela.", file=sys.stderr)
        return 6
    print(f"\nFalta uma coisa que só se faz no painel: desativar a expiração da "
          f"chave de nó de '{nome}'.\n"
          f"  1. Abra https://login.tailscale.com/admin/machines\n"
          f"  2. Ache a máquina '{nome}'\n"
          f"  3. No menu dela, escolha 'Disable key expiry'\n")
    _aguardar("Feito isso, aperte Enter para eu conferir. ")
    try:
        expiracao = mod_rede.expiracao_de(_status_da_rede(tailscale), nome)
    except (mod_rede.ErroDeRede, ValueError) as erro:
        print(str(erro), file=sys.stderr)
        return 6
    if expiracao is not None:
        print(f"a expiração de '{nome}' continua ativa, vencendo em {expiracao}. "
              f"Não vou anunciar sucesso: quando essa data chegar, a máquina sai "
              f"da rede e o acesso vai embora junto.", file=sys.stderr)
        return 6
    print(f"conferido: a chave de nó de '{nome}' não expira mais.")
    return 0


def _preparar_maquina(opcoes) -> int:
    lido = mod_manifesto.ler_ou_vazio(Path(opcoes.cadastro))
    caminho_da_chave = lido.caminho_da_chave()
    if caminho_da_chave is None:
        print("não há chave declarada no manifesto. Rode 'castor chave criar' "
              "antes de preparar uma máquina.", file=sys.stderr)
        return 1

    contexto = {"chave": caminho_da_chave}
    roteiro = mod_preparar.montar_roteiro(
        nome=opcoes.nome, endereco=opcoes.endereco,
        usuario_inicial=opcoes.usuario_inicial,
        usuario_de_servico=opcoes.usuario_de_servico,
        chave_publica=mod_chaves.mostrar(caminho_da_chave), contexto=contexto,
        chave_inicial=opcoes.chave_inicial)
    try:
        mod_preparar.executar(roteiro, contexto)
    except mod_conexao.FalhaDeConexao as erro:
        print(str(erro), file=sys.stderr)
        return CODIGOS.get(type(erro), 5)
    except (mod_preparar.ErroDePreparo, mod_medicao.MedicaoIncompleta) as erro:
        print(str(erro), file=sys.stderr)
        return 7

    if contexto.get("url_de_login"):
        print(f"\nAbra este endereço no navegador desta máquina para ligar "
              f"'{opcoes.nome}' à sua rede privada:\n\n  "
              f"{contexto['url_de_login']}\n")
        _aguardar("Depois de autorizar, aperte Enter. ")

    medido = contexto["medicao"]
    da_conta = contexto["medicao_servico"]
    nota = mod_medicao.conferir_fuso(medido, fuso_daqui=time.strftime("%z"))
    if nota:
        print(f"[castor] {nota}")

    # Grava ANTES da conferência de expiração: a cliente tecnicamente pronta
    # não pode sumir do cadastro porque o painel do Tailscale segue pendente
    # (medido no macbook do Walter — código 6 abortava com cadastro vazio).
    maquina = mod_manifesto.Maquina(
        nome=opcoes.nome, usuario=opcoes.usuario_de_servico,
        casa=f"/home/{opcoes.usuario_de_servico}", sistema=medido.sistema,
        endereco=opcoes.endereco, python=da_conta.python, papel="cliente")
    mod_manifesto.gravar(mod_manifesto.acrescentar(lido, maquina, substituir=True))

    # O roteiro monta os próprios destinos e não expõe nenhum; aqui a conexão é
    # com o usuário de serviço, pela chave do castor, que o roteiro provou.
    destino_ssh = mod_conexao.Destino(usuario=opcoes.usuario_de_servico,
                                      endereco=opcoes.endereco,
                                      chave=caminho_da_chave)
    servico_de_aviso = (lido.dados.get("aviso") or {}).get("servico", "correio")
    # Relê: o manifesto acabou de ser gravado com a máquina nova, e é dela que a
    # resolução de $HOME precisa.
    declarados = mod_manifesto.ler(Path(opcoes.cadastro))
    falha_de_entrega = None
    if servico_de_aviso in declarados.dados.get("servicos", {}):
        try:
            _entregar(declarados, servico_de_aviso, opcoes.nome, destino_ssh)
        except (mod_conexao.FalhaDeConexao, mod_cofre.ErroDeCofre) as erro:
            falha_de_entrega = erro

    codigo = _conduzir_expiracao(opcoes.nome)
    if falha_de_entrega is not None:
        print(f"a máquina '{opcoes.nome}' está pronta e cadastrada, mas a "
              f"entrega do aviso falhou: {falha_de_entrega}", file=sys.stderr)
        return 5
    if codigo != 0:
        print(f"a máquina '{opcoes.nome}' está pronta e cadastrada; ficou "
              f"pendente: desativar a expiração da chave de nó no painel e "
              f"rodar o preparar de novo para conferir.", file=sys.stderr)
        return codigo

    entregou_aviso = servico_de_aviso in declarados.dados.get("servicos", {})
    if entregou_aviso:
        print(f"\n'{opcoes.nome}' está pronta, cadastrada e sabendo avisar por "
              f"e-mail quando algo falhar.")
        return 0

    print(f"\n'{opcoes.nome}' está pronta e cadastrada. Ela ainda não sabe "
          f"avisar quando algo falhar: declare o serviço '{servico_de_aviso}' "
          f"em 'servicos' do manifesto e rode 'castor segredos enviar "
          f"{servico_de_aviso} --maquina {opcoes.nome}'.")
    return 0


def _despachar_maquina(opcoes) -> int:
    if opcoes.verbo == "preparar":
        return _preparar_maquina(opcoes)
    if opcoes.verbo == "adicionar":
        return _adicionar_maquina(opcoes)
    if opcoes.verbo == "listar":
        lido = mod_manifesto.ler(Path(opcoes.cadastro))
        for nome in lido.nomes():
            declarada = lido.maquina(nome)
            print(f"{nome}\t{declarada.papel}\t{declarada.endereco or '-'}"
                  f"\t{declarada.usuario}\t{declarada.sistema}")
        return 0
    if opcoes.verbo == "remover":
        lido = mod_manifesto.ler(Path(opcoes.cadastro))
        mod_manifesto.gravar(mod_manifesto.retirar(lido, opcoes.nome))
        print(f"retirada do manifesto: {opcoes.nome}. Isto não desfaz nada na "
              f"máquina — chave, usuário e serviços continuam lá.")
        return 0
    if opcoes.verbo == "testar":
        destino = _destino_de(opcoes, opcoes.nome)
        try:
            versao = mod_conexao.versao_remota(destino)
        except mod_conexao.FalhaDeConexao as erro:
            print(str(erro), file=sys.stderr)
            return CODIGOS.get(type(erro), 5)
        print(f"{opcoes.nome}: de pé, castor {versao}")
        return 0
    return 1


def principal(argumentos: list[str] | None = None) -> int:
    analisador = construir_analisador()
    opcoes = analisador.parse_args(argumentos)
    if not opcoes.cadastro:
        opcoes.cadastro = str(mod_cadastro.resolver())
    if opcoes.versao:
        print(castor.__version__)
        return 0
    if opcoes.area is None:
        analisador.print_help()
        return 1
    try:
        if opcoes.area == "configurar":
            return mod_configurar.rodar(Path(opcoes.cadastro))
        if opcoes.area == "chave":
            return _despachar_chave(opcoes)
        if opcoes.area == "maquina":
            return _despachar_maquina(opcoes)
        if opcoes.area == "atualizacao":
            try:
                return _despachar_atualizacao(opcoes)
            except mod_atualizacao.AlvoInvalido as erro:
                print(str(erro), file=sys.stderr)
                return 1
            except mod_conexao.FalhaDeConexao as erro:
                print(str(erro), file=sys.stderr)
                return CODIGOS.get(type(erro), 5)
        if opcoes.area == "ronda":
            try:
                return _despachar_ronda(opcoes)
            except mod_ronda.ChecagemInvalida as erro:
                print(str(erro), file=sys.stderr)
                return 1
            except mod_conexao.FalhaDeConexao as erro:
                print(str(erro), file=sys.stderr)
                return CODIGOS.get(type(erro), 5)
        if opcoes.area == "servico":
            try:
                return _despachar_servico(opcoes)
            except mod_conexao.FalhaDeConexao as erro:
                print(str(erro), file=sys.stderr)
                return CODIGOS.get(type(erro), 5)
            except ServicoNaoObedeceu as erro:
                print(str(erro), file=sys.stderr)
                return CODIGO_DE_SERVICO
            except mod_unidade.DeclaracaoInvalida as erro:
                print(str(erro), file=sys.stderr)
                return 1
        if opcoes.area == "segredos":
            return _despachar_segredos(opcoes)
        if opcoes.area == "rotina":
            return _despachar_rotina(opcoes)
    except (ErroDeManifesto, mod_chaves.ErroDeChave,
            mod_cofre.ErroDeCofre) as erro:
        print(str(erro), file=sys.stderr)
        return 1
    print(f"área '{opcoes.area}' ainda não tem verbos nesta versão.", file=sys.stderr)
    return 1


def executar() -> None:
    raise SystemExit(principal())
