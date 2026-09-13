import argparse
import getpass
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import castor
from castor import chaves as mod_chaves
from castor import conexao as mod_conexao
from castor import medicao as mod_medicao
from castor import manifesto as mod_manifesto
from castor import segredos as mod_segredos
from castor.manifesto import ErroDeManifesto

AREAS = ("chave", "maquina", "segredos", "servico", "rotina", "ronda",
         "atualizacao")


def construir_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="castor",
        description="Toolkit de infra pessoal: chave, máquina, segredos, "
                    "serviço, rotina, ronda e atualização.",
    )
    analisador.add_argument("--versao", action="store_true",
                            help="imprime a versão do castor e sai")
    analisador.add_argument(
        "--manifesto",
        default=os.environ.get("CASTOR_MANIFESTO", "castor.json"),
        help="caminho do manifesto (default: $CASTOR_MANIFESTO ou ./castor.json)",
    )
    areas = analisador.add_subparsers(dest="area", metavar="area")

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

    testar = verbos_maquina.add_parser("testar", help="prova a conexão com a cliente")
    testar.add_argument("nome")

    segredos = areas.add_parser("segredos", help="área segredos")
    verbos = segredos.add_subparsers(dest="verbo", metavar="verbo", required=True)

    gerar = verbos.add_parser("gerar", help="resolve o modelo e grava o arquivo de serviço")
    gerar.add_argument("modelo")
    gerar.add_argument("--maquina", required=True)
    gerar.add_argument("--destino", required=True)

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

    for nome in AREAS:
        if nome not in ("chave", "maquina", "segredos", "rotina"):
            areas.add_parser(nome, help=f"área {nome}")
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

    config = mod_manifesto.ler(Path(opcoes.manifesto)).dados.get("aviso") or {}
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

    declarado = mod_manifesto.ler(Path(opcoes.manifesto)).dados.get("rotinas", {})
    if opcoes.nome not in declarado:
        print(f"rotina '{opcoes.nome}' não está declarada no manifesto "
              f"{opcoes.manifesto}.", file=sys.stderr)
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


def _despachar_segredos(opcoes) -> int:
    if opcoes.verbo == "gerar":
        maquina = mod_manifesto.ler(Path(opcoes.manifesto)).maquina(opcoes.maquina)
        destino = mod_segredos.gerar(Path(opcoes.modelo), maquina, Path(opcoes.destino))
        print(f"gravado: {destino}")
        return 0
    print(mod_segredos.ver(Path(opcoes.arquivo), opcoes.variavel, revelar=opcoes.revelar))
    return 0


def _caminho_da_chave(opcoes) -> Path:
    declarado = mod_manifesto.ler_ou_vazio(Path(opcoes.manifesto)).caminho_da_chave()
    return declarado or mod_chaves.caminho_padrao()


def _anotar_chave(opcoes, privada: Path) -> None:
    lido = mod_manifesto.ler_ou_vazio(Path(opcoes.manifesto))
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
    lido = mod_manifesto.ler(Path(opcoes.manifesto))
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
    lido = mod_manifesto.ler_ou_vazio(Path(opcoes.manifesto))
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


def _despachar_maquina(opcoes) -> int:
    if opcoes.verbo == "adicionar":
        return _adicionar_maquina(opcoes)
    if opcoes.verbo == "listar":
        lido = mod_manifesto.ler(Path(opcoes.manifesto))
        for nome in lido.nomes():
            declarada = lido.maquina(nome)
            print(f"{nome}\t{declarada.papel}\t{declarada.endereco or '-'}"
                  f"\t{declarada.usuario}\t{declarada.sistema}")
        return 0
    if opcoes.verbo == "remover":
        lido = mod_manifesto.ler(Path(opcoes.manifesto))
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
    if opcoes.versao:
        print(castor.__version__)
        return 0
    if opcoes.area is None:
        analisador.print_help()
        return 1
    try:
        if opcoes.area == "chave":
            return _despachar_chave(opcoes)
        if opcoes.area == "maquina":
            return _despachar_maquina(opcoes)
        if opcoes.area == "segredos":
            return _despachar_segredos(opcoes)
        if opcoes.area == "rotina":
            return _despachar_rotina(opcoes)
    except (ErroDeManifesto, mod_chaves.ErroDeChave) as erro:
        print(str(erro), file=sys.stderr)
        return 1
    print(f"área '{opcoes.area}' ainda não tem verbos nesta versão.", file=sys.stderr)
    return 1


def executar() -> None:
    raise SystemExit(principal())
