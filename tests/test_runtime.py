import hashlib
from pathlib import Path

import pytest

from castor import runtime
from servidor import ServidorDeArquivos


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
