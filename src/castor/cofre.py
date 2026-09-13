"""O cofre: um arquivo de CHAVE=valor na máquina principal.

Um arquivo concentra tudo, e o raio de dano é maior que o de segredos separados
por serviço. Para uma pessoa com duas máquinas é a troca certa; para uma frota
não seria. O que compensa o risco é a filtragem: cada serviço recebe só as
chaves declaradas para ele, e o cofre nunca sai da principal.

Nenhum comando escreve aqui. O cofre é editado por quem é dono dele.
"""
from pathlib import Path


class ErroDeCofre(Exception):
    """Base dos erros desta área."""


class CofreAusente(ErroDeCofre):
    pass


class CofreFrouxo(ErroDeCofre):
    pass


class ChaveAusenteNoCofre(ErroDeCofre):
    pass


def ler(caminho: Path) -> dict[str, str]:
    caminho = Path(caminho).expanduser()
    if not caminho.exists():
        raise CofreAusente(
            f"não achei o cofre em {caminho}. Crie o arquivo com uma atribuição "
            f"por linha (CHAVE=valor) e rode 'chmod 600 {caminho}'."
        )
    if caminho.stat().st_mode & 0o077:
        raise CofreFrouxo(
            f"{caminho} pode ser lido por outros usuários da máquina. "
            f"Rode 'chmod 600 {caminho}' e tente de novo."
        )
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#") or "=" not in limpa:
            continue
        chave, valor = limpa.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"')
    return valores


def filtrar(valores: dict[str, str], chaves: list[str], *,
            origem) -> dict[str, str]:
    """Só o que cabe ao serviço. O erro nomeia o que falta, nunca o que existe."""
    faltando = [chave for chave in chaves if chave not in valores]
    if faltando:
        raise ChaveAusenteNoCofre(
            f"o cofre em {origem} não tem {', '.join(faltando)}. "
            f"Acrescente a linha e rode de novo."
        )
    return {chave: valores[chave] for chave in chaves}
