import subprocess
import sys
import zipfile


def construir(tmp_path):
    alvo = tmp_path / "castor.pyz"
    feito = subprocess.run(
        [sys.executable, "scripts/build-pyz.py", "--saida", str(alvo)],
        capture_output=True, text=True,
    )
    assert feito.returncode == 0, feito.stderr
    return alvo


def test_pacote_roda_e_enumera_as_areas(tmp_path):
    alvo = construir(tmp_path)
    saida = subprocess.run([sys.executable, str(alvo), "--help"], capture_output=True, text=True)
    assert saida.returncode == 0
    assert "segredos" in saida.stdout


def test_pacote_propaga_codigo_de_saida(tmp_path):
    # Manifesto ausente devolve 1. Se o ponto de entrada descartar o retorno,
    # o pacote sai 0 e a falha some.
    #
    # Antes isto media uma "area sem verbos", e a ultima delas ganhou os seus
    # no plano 7 — a cobaia acabou, o invariante nao. Manifesto ausente e uma
    # falha que nao depende de nenhuma area estar incompleta.
    alvo = construir(tmp_path)
    saida = subprocess.run(
        [sys.executable, str(alvo), "--cadastro",
         str(tmp_path / "nao-existe.json"), "maquina", "listar"],
        capture_output=True, text=True)
    assert saida.returncode == 1


def test_pacote_nao_leva_codigo_nativo(tmp_path):
    alvo = construir(tmp_path)
    with zipfile.ZipFile(alvo) as pacote:
        nativos = [n for n in pacote.namelist() if n.endswith((".so", ".pyd", ".dll"))]
    assert nativos == []


# Roda de dentro do pyz: é dali que um mentorado roda o preparar, e foi o
# __file__ do pyz que escondeu o instalador (#1251). Teste que importa do
# checkout acha scripts/ e passa sem provar nada.
_PREPARAR_DO_PYZ = """
import json, sys
sys.path.insert(0, sys.argv[1])
from castor import conexao, preparar

RESPOSTA = ("usuario=castor\\ncasa=/home/castor\\nsistema=Linux\\n"
            "epoca=1789000000\\nfuso=-0400\\npython=Python 3.11.2\\nsudo=nao\\n")
entradas = []

def executor(destino, comando, **opcoes):
    if opcoes.get("entrada"):
        entradas.append(opcoes["entrada"])
    texto = RESPOSTA if "usuario=" in comando else ""
    return conexao.Saida(codigo=0, texto=texto, erro="")

contexto = {}
roteiro = {p.nome: p for p in preparar.montar_roteiro(
    nome="x", endereco="x.exemplo.test", usuario_inicial="i",
    usuario_de_servico="castor", chave_publica="ssh-ed25519 AAAA a",
    contexto=contexto, executor=executor, agora=lambda: 1789000000,
    quer_node=True, base_da_release=sys.argv[2])}
roteiro["python_da_conta"].fazer(contexto)
roteiro["node_da_conta"].fazer(contexto)
print(json.dumps(entradas))
"""


def test_preparar_do_pyz_acha_os_dois_instaladores(tmp_path):
    import hashlib
    import json
    from pathlib import Path

    from servidor import ServidorDeArquivos

    mapa = {}
    for nome in ("node", "python"):
        corpo = Path(f"scripts/instalar-{nome}.sh").read_bytes()
        mapa[f"/instalar-{nome}.sh"] = corpo
        mapa[f"/instalar-{nome}.sh.sha256"] = (
            hashlib.sha256(corpo).hexdigest().encode() + b"\n")
    alvo = construir(tmp_path)
    roteiro = tmp_path / "roda_do_pyz.py"
    roteiro.write_text(_PREPARAR_DO_PYZ, encoding="utf-8")
    servidor = ServidorDeArquivos(mapa)
    try:
        feito = subprocess.run(
            [sys.executable, "-I", str(roteiro), str(alvo), servidor.base],
            capture_output=True, text=True, cwd=tmp_path)
    finally:
        servidor.fechar()
    assert feito.returncode == 0, feito.stderr
    entradas = json.loads(feito.stdout)
    assert len(entradas) == 2
    assert any("NODE_VERSION" in e for e in entradas)
    assert entradas[0] == mapa["/instalar-python.sh"].decode()
