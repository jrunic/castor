"""O que cada tipo de alvo roda para se atualizar, e como se confere depois.

Funções puras sobre a declaração: entra o alvo, sai o comando. A decisão de
empurrar da principal — em vez de cada máquina se atualizar sozinha — vive no
cli; aqui ficam só as formas de cada tipo.

Sem idade mínima, confiança ou janela de aprovação: isso é governança de frota,
e esta versão não tem. O material diz isso em voz alta, para ninguém achar que
há política onde não há.
"""
INSTALADOR = ("https://raw.githubusercontent.com/jrunic/castor/main/"
              "scripts/instalar.sh")
TIPOS = ("castor", "pipx", "npm", "comando")


class AlvoInvalido(Exception):
    pass


def comando_de(declarado: dict) -> str:
    tipo = declarado.get("tipo")
    if tipo not in TIPOS:
        raise AlvoInvalido(
            f"o alvo é do tipo '{tipo}', que não existe. Use um de: "
            f"{', '.join(TIPOS)}.")
    if tipo == "castor":
        # O instalador confere a soma publicada — é ele que cumpre o critério 15.
        return f"curl -fsSL {INSTALADOR} | sh"
    if tipo == "comando":
        if not declarado.get("comando"):
            raise AlvoInvalido("o alvo é do tipo comando e não declara 'comando'.")
        return declarado["comando"]
    if not declarado.get("pacote"):
        raise AlvoInvalido(f"o alvo é do tipo {tipo} e não declara 'pacote'.")
    if tipo == "pipx":
        return f"pipx upgrade {declarado['pacote']}"
    return f"npm update -g {declarado['pacote']}"


def comando_de_versao(nome: str, declarado: dict) -> str:
    """Como perguntar a versão. Sem declaração, pergunta se o comando responde.

    Conferir que o gerenciador de pacotes saiu zero não prova que o programa
    roda — e atualizar deixando o comando quebrado, em silêncio, é o pior
    desfecho.
    """
    if declarado.get("versao"):
        return declarado["versao"]
    if declarado.get("tipo") == "castor":
        from castor import conexao as mod_conexao
        # Com o PATH corrigido: ~/.local/bin fica fora do PATH do ssh
        # não-interativo, e na principal pode estar fora do PATH do shell que o
        # subprocesso abre. A mesma linha serve aos dois casos.
        return mod_conexao.comando_remoto("--versao")
    return f"command -v {nome} >/dev/null 2>&1 && echo presente || true"


def concluir(nome: str, antes: str, depois: str) -> tuple:
    """Devolve (situação, passou). Versão igual não é falha: já estava em dia."""
    if not depois.strip():
        return (f"'{nome}' não respondeu depois da atualização", False)
    if not antes.strip():
        return (f"'{nome}' passou a responder: {depois.strip()}", True)
    if antes.strip() == depois.strip():
        return ("sem mudança", True)
    return (f"{antes.strip()} → {depois.strip()}", True)
