import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INSTALADOR = RAIZ / "scripts" / "instalar.sh"


def construir(tmp_path):
    artefato = tmp_path / "castor.pyz"
    feito = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "build-pyz.py"),
         "--saida", str(artefato)],
        capture_output=True, text=True,
    )
    assert feito.returncode == 0, feito.stderr
    return artefato


def com_python_novo(tmp_path):
    """Põe um python3 >= 3.12 no PATH.

    No macOS o python3 do sistema é 3.9 e o instalador o recusa — de propósito.
    Sem este atalho, o teste de instalação mediria a máquina, não o instalador.
    """
    atalhos = tmp_path / "atalhos"
    atalhos.mkdir(exist_ok=True)
    ponte = atalhos / "python3"
    if not ponte.exists():
        ponte.symlink_to(sys.executable)
    return f"{atalhos}:{os.environ['PATH']}"


def instalar(tmp_path, **ambiente):
    return subprocess.run(
        ["sh", str(INSTALADOR)],
        env={**os.environ, **ambiente}, capture_output=True, text=True,
    )


def test_o_instalador_existe_e_e_executavel():
    assert INSTALADOR.exists()
    assert os.access(INSTALADOR, os.X_OK)


def test_cabe_em_cem_linhas():
    """Restrição do CONTEXTO.md: o único shell do produto não cresce."""
    assert len(INSTALADOR.read_text(encoding="utf-8").splitlines()) < 100


def test_e_sh_e_para_no_primeiro_erro():
    texto = INSTALADOR.read_text(encoding="utf-8")
    assert texto.startswith("#!/bin/sh")
    assert "set -eu" in texto


def test_sintaxe_valida():
    concluido = subprocess.run(["sh", "-n", str(INSTALADOR)],
                               capture_output=True, text=True)
    assert concluido.returncode == 0, concluido.stderr


def test_instala_de_artefato_local_e_o_comando_responde(tmp_path):
    """Ponta a ponta, sem rede: CASTOR_ARTEFATO substitui o download."""
    artefato = construir(tmp_path)
    destino = tmp_path / "bin"
    concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                         CASTOR_ARTEFATO=str(artefato),
                         CASTOR_DESTINO=str(destino))
    assert concluido.returncode == 0, concluido.stderr

    instalado = destino / "castor"
    assert instalado.exists() and os.access(instalado, os.X_OK)
    resposta = subprocess.run([str(instalado), "--versao"], capture_output=True,
                              text=True)
    assert resposta.returncode == 0
    assert resposta.stdout.strip()


def test_instalar_duas_vezes_nao_quebra_a_instalacao(tmp_path):
    """A atualização do castor passa por aqui — instalar por cima tem de valer."""
    artefato = construir(tmp_path)
    destino = tmp_path / "bin"
    for _ in range(2):
        concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                             CASTOR_ARTEFATO=str(artefato),
                             CASTOR_DESTINO=str(destino))
        assert concluido.returncode == 0, concluido.stderr
    resposta = subprocess.run([str(destino / "castor"), "--versao"],
                              capture_output=True, text=True)
    assert resposta.returncode == 0


def test_artefato_que_nao_responde_como_castor_nao_e_instalado(tmp_path):
    """Instalador que termina em zero sem comando de pé é o defeito da classe."""
    impostor = tmp_path / "impostor.pyz"
    impostor.write_text("isto não é um castor\n", encoding="utf-8")
    destino = tmp_path / "bin"
    concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                         CASTOR_ARTEFATO=str(impostor),
                         CASTOR_DESTINO=str(destino))
    assert concluido.returncode != 0
    assert "não respondeu como castor" in concluido.stderr
    assert not (destino / "castor").exists()


def test_python_velho_e_recusado_antes_de_instalar_qualquer_coisa(tmp_path):
    """Sem isto, o castor instala e só quebra na primeira execução."""
    falso = tmp_path / "python3"
    falso.write_text("#!/bin/sh\necho 'Python 3.9.6'\n", encoding="utf-8")
    falso.chmod(0o755)
    destino = tmp_path / "bin"
    concluido = instalar(tmp_path, PATH=f"{tmp_path}:{os.environ['PATH']}",
                         CASTOR_ARTEFATO="/nao/importa",
                         CASTOR_DESTINO=str(destino))
    assert concluido.returncode != 0
    assert "3.12" in concluido.stderr
    assert not destino.exists()


def test_o_comando_instalado_nao_depende_do_python3_do_PATH(tmp_path):
    """O envoltório fixa o interpretador que passou na conferência.

    No macOS o python3 do PATH é 3.9: sem fixar, o castor instala com um
    interpretador e roda com outro — e quebra na primeira execução, depois de
    o instalador ter anunciado sucesso.
    """
    artefato = construir(tmp_path)
    destino = tmp_path / "bin"
    concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                         CASTOR_ARTEFATO=str(artefato),
                         CASTOR_DESTINO=str(destino))
    assert concluido.returncode == 0, concluido.stderr

    sem_atalho = subprocess.run(
        [str(destino / "castor"), "--versao"],
        env={**os.environ, "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert sem_atalho.returncode == 0, sem_atalho.stderr
    assert sem_atalho.stdout.strip()


def servidor_de_arquivos(mapa, codigo_padrao=404):
    """Servidor HTTP em localhost que serve só o que está no mapa.

    Sem rede externa no teste: o que se mede aqui é o instalador, não a internet.
    """
    import http.server
    import threading

    class Atendente(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            corpo = mapa.get(self.path)
            if corpo is None:
                self.send_response(codigo_padrao)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *args):
            pass

    servidor = http.server.HTTPServer(("127.0.0.1", 0), Atendente)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_port}/castor.pyz"


def servidor_que_responde(codigo, corpo=b""):
    mapa = {"/castor.pyz": corpo} if codigo == 200 else {}
    return servidor_de_arquivos(mapa, codigo_padrao=codigo)


def test_release_que_nao_existe_nao_e_relatada_como_falta_de_internet(tmp_path):
    """404 manda conferir a release; culpar a rede manda procurar no lugar errado.

    Medido em 13/09/2026 na bancada: sem release publicada, o instalador dizia
    'a máquina tem saída para a internet?' numa máquina com internet.
    """
    servidor, url = servidor_que_responde(404)
    try:
        concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                             CASTOR_URL=url,
                             CASTOR_DESTINO=str(tmp_path / "bin"))
    finally:
        servidor.shutdown()
        servidor.server_close()
    assert concluido.returncode != 0
    assert "release" in concluido.stderr
    assert "internet" not in concluido.stderr


def test_servidor_fora_do_ar_continua_sendo_relatado_como_rede(tmp_path):
    servidor, url = servidor_que_responde(200)
    servidor.shutdown()
    servidor.server_close()  # fecha o socket: porta que aceita e não serve trava
    concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                         CASTOR_URL=url, CASTOR_DESTINO=str(tmp_path / "bin"))
    assert concluido.returncode != 0
    assert "internet" in concluido.stderr


def soma_de(caminho):
    import hashlib
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def test_a_versao_do_pacote_bate_com_a_do_pyproject():
    """Duas versões que divergem viram release anunciando o que não entregou."""
    import tomllib
    with (RAIZ / "pyproject.toml").open("rb") as arquivo:
        declarada = tomllib.load(arquivo)["project"]["version"]
    import castor
    assert castor.__version__ == declarada


def test_instala_quando_o_arquivo_bate_com_a_soma_publicada(tmp_path):
    artefato = construir(tmp_path)
    soma = f"{soma_de(artefato)}  castor.pyz\n".encode()
    servidor, url = servidor_de_arquivos({"/castor.pyz": artefato.read_bytes(),
                                          "/castor.pyz.sha256": soma})
    destino = tmp_path / "bin"
    try:
        concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                             CASTOR_URL=url, CASTOR_DESTINO=str(destino))
    finally:
        servidor.shutdown()
        servidor.server_close()
    assert concluido.returncode == 0, concluido.stderr
    assert (destino / "castor").exists()


def test_arquivo_que_nao_bate_com_a_soma_nao_e_instalado(tmp_path):
    """Sem isto, o instalador executa o que quer que o servidor tenha entregue."""
    artefato = construir(tmp_path)
    outra = "0" * 64
    servidor, url = servidor_de_arquivos({
        "/castor.pyz": artefato.read_bytes(),
        "/castor.pyz.sha256": f"{outra}  castor.pyz\n".encode()})
    destino = tmp_path / "bin"
    try:
        concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                             CASTOR_URL=url, CASTOR_DESTINO=str(destino))
    finally:
        servidor.shutdown()
        servidor.server_close()
    assert concluido.returncode != 0
    assert "soma" in concluido.stderr
    assert not (destino / "castor").exists()


def test_soma_ausente_recusa_em_vez_de_instalar_no_escuro(tmp_path):
    artefato = construir(tmp_path)
    servidor, url = servidor_de_arquivos({"/castor.pyz": artefato.read_bytes()})
    destino = tmp_path / "bin"
    try:
        concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                             CASTOR_URL=url, CASTOR_DESTINO=str(destino))
    finally:
        servidor.shutdown()
        servidor.server_close()
    assert concluido.returncode != 0
    assert "soma" in concluido.stderr
    assert not (destino / "castor").exists()


def test_quem_dispensa_a_soma_dispensa_por_escrito(tmp_path):
    artefato = construir(tmp_path)
    servidor, url = servidor_de_arquivos({"/castor.pyz": artefato.read_bytes()})
    destino = tmp_path / "bin"
    try:
        concluido = instalar(tmp_path, PATH=com_python_novo(tmp_path),
                             CASTOR_URL=url, CASTOR_DESTINO=str(destino),
                             CASTOR_SEM_SOMA="1")
    finally:
        servidor.shutdown()
        servidor.server_close()
    assert concluido.returncode == 0, concluido.stderr
    assert (destino / "castor").exists()
