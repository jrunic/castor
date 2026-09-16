import hashlib
import threading
import http.server
from pathlib import Path

import pytest

from castor import runtime


class ServidorDeArquivos:
    def __init__(self, mapa, codigo_padrao=404):
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

        self.servidor = http.server.HTTPServer(("127.0.0.1", 0), Atendente)
        threading.Thread(target=self.servidor.serve_forever,
                         daemon=True).start()

    @property
    def base(self):
        return f"http://127.0.0.1:{self.servidor.server_port}"

    def fechar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


def _soma(bytes_):
    return hashlib.sha256(bytes_).hexdigest().encode() + b"\n"


def test_baixar_irmao_confere_a_soma_e_devolve_o_caminho(tmp_path):
    script = b"#!/bin/sh\necho ok\n"
    servidor = ServidorDeArquivos({
        "/instalar-node.sh": script,
        "/instalar-node.sh.sha256": _soma(script),
    })
    try:
        caminho = runtime.baixar_irmao("node", servidor.base)
    finally:
        servidor.fechar()
    assert Path(caminho).read_bytes() == script


def test_baixar_irmao_recusa_quando_a_soma_nao_bate(tmp_path):
    servidor = ServidorDeArquivos({
        "/instalar-node.sh": b"#!/bin/sh\necho ok\n",
        "/instalar-node.sh.sha256": b"0" * 64 + b"\n",
    })
    try:
        with pytest.raises(runtime.ErroDeRuntime) as erro:
            runtime.baixar_irmao("node", servidor.base)
    finally:
        servidor.fechar()
    assert "soma" in str(erro.value)


def test_baixar_irmao_recusa_sem_soma_publicada(tmp_path):
    servidor = ServidorDeArquivos({
        "/instalar-node.sh": b"#!/bin/sh\necho ok\n",
    })
    try:
        with pytest.raises(runtime.ErroDeRuntime) as erro:
            runtime.baixar_irmao("node", servidor.base)
    finally:
        servidor.fechar()
    assert "soma" in str(erro.value)
