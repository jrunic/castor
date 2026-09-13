from dataclasses import dataclass
from email.message import EmailMessage

LIMITE_DO_CORPO = 4000


@dataclass(frozen=True)
class Aviso:
    alarme: str
    maquina: str
    assunto_extra: str
    corpo: str


def montar_mensagem(aviso: Aviso, de: str, para: str) -> EmailMessage:
    mensagem = EmailMessage()
    mensagem["From"] = de
    mensagem["To"] = para
    assunto = f"[castor/{aviso.maquina}] {aviso.alarme}"
    if aviso.assunto_extra:
        assunto = f"{assunto} — {aviso.assunto_extra}"
    mensagem["Subject"] = assunto

    corpo = aviso.corpo
    if len(corpo) > LIMITE_DO_CORPO:
        # O fim do registro é o que interessa: é onde o erro aparece.
        corpo = "[...truncado]\n" + corpo[-LIMITE_DO_CORPO:]
    mensagem.set_content(corpo)
    return mensagem
