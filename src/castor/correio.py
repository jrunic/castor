import smtplib
from collections.abc import Callable
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


class RemetenteSMTP:
    """Fronteira de sistema. `abrir` existe para o teste não tocar a rede."""

    def __init__(self, servidor: str, porta: int, usuario: str, senha: str,
                 abrir: Callable | None = None) -> None:
        self._servidor = servidor
        self._porta = porta
        self._usuario = usuario
        self.__senha = senha
        self._abrir = abrir or (lambda s, p: smtplib.SMTP(s, p, timeout=30))

    def __repr__(self) -> str:
        # Sem a senha: repr vaza em log e em rastreamento de erro.
        return f"RemetenteSMTP(servidor={self._servidor!r}, usuario={self._usuario!r})"

    def enviar(self, mensagem: EmailMessage) -> None:
        with self._abrir(self._servidor, self._porta) as cliente:
            cliente.starttls()  # porta 587 com STARTTLS — a assumption 4 da spec
            cliente.login(self._usuario, self.__senha)
            cliente.send_message(mensagem)
