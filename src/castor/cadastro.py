import os
from pathlib import Path


def _xdg_config() -> Path:
    bruto = os.environ.get("XDG_CONFIG_HOME", "")
    if not bruto or not Path(bruto).is_absolute():
        return Path.home() / ".config"
    return Path(bruto)


def resolver() -> Path:
    env = os.environ.get("CASTOR_CADASTRO", "")
    if env and Path(env).is_absolute():
        return Path(env)
    pasta = _xdg_config() / "castor"
    novo = pasta / "cadastro.json"
    antigo = pasta / "castor.json"
    if novo.exists():
        return novo
    if antigo.exists():
        return antigo
    return novo


def origem_para_gravar(lido_ou_path: Path) -> Path:
    caminho = Path(lido_ou_path)
    if caminho.name == "castor.json":
        return caminho.with_name("cadastro.json")
    return caminho
