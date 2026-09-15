from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROIBIDO = ("--seco",)


def _docs():
    arquivos = [RAIZ / "README.md", RAIZ / "CONTEXTO.md"]
    arquivos.extend(sorted((RAIZ / "docs").rglob("*.md")))
    return [p for p in arquivos if p.name != "CHANGELOG.md" and p.exists()]


def test_superficie_nao_fala_seco():
    for path in _docs():
        texto = path.read_text(encoding="utf-8")
        assert "--seco" not in texto, path


def test_superficie_nao_fala_manifesto():
    for path in _docs():
        texto = path.read_text(encoding="utf-8")
        assert "manifesto" not in texto.lower(), path
