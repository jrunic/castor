import hashlib
from pathlib import Path

import pytest

import castor
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


def _servir_a_versao(monkeypatch, servidor, versao="9.9.9"):
    monkeypatch.setattr("castor.runtime.ORIGEM_DAS_RELEASES", servidor.base)
    monkeypatch.setattr(castor, "__version__", versao)


def test_base_da_versao_aponta_para_a_tag_da_versao_em_execucao(monkeypatch):
    monkeypatch.setattr("castor.runtime.ORIGEM_DAS_RELEASES",
                        "https://exemplo.test/releases/download")
    monkeypatch.setattr(castor, "__version__", "9.9.9")
    assert runtime.base_da_versao() == (
        "https://exemplo.test/releases/download/v9.9.9")


def test_baixar_irmao_sem_base_pede_a_release_da_versao(monkeypatch):
    script = b"#!/bin/sh\necho ok\n"
    servidor = ServidorDeArquivos({
        "/v9.9.9/instalar-node.sh": script,
        "/v9.9.9/instalar-node.sh.sha256": _soma(script),
    })
    try:
        _servir_a_versao(monkeypatch, servidor)
        caminho = runtime.baixar_irmao("node")
    finally:
        servidor.fechar()
    assert Path(caminho).read_bytes() == script
    assert servidor.pedidos == ["/v9.9.9/instalar-node.sh",
                                "/v9.9.9/instalar-node.sh.sha256"]


def test_release_da_versao_ausente_nomeia_a_tag_e_nao_cai_para_a_mais_recente(
        monkeypatch):
    script = b"#!/bin/sh\necho ok\n"
    servidor = ServidorDeArquivos({
        "/instalar-node.sh": script,
        "/instalar-node.sh.sha256": _soma(script),
        "/latest/download/instalar-node.sh": script,
        "/latest/download/instalar-node.sh.sha256": _soma(script),
    })
    try:
        _servir_a_versao(monkeypatch, servidor)
        with pytest.raises(runtime.ErroDeRuntime) as erro:
            runtime.baixar_irmao("node")
    finally:
        servidor.fechar()
    assert "v9.9.9" in str(erro.value)
    assert servidor.pedidos, "o teste não pediu nada: não prova ausência de queda"
    assert all(p.startswith("/v9.9.9/") for p in servidor.pedidos)
