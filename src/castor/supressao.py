import json
from pathlib import Path


class Supressor:
    """Guarda quando cada alarme foi avisado pela última vez.

    O relógio entra por parâmetro: teste de janela que depende da hora real é
    teste que falha sozinho de madrugada.
    """

    def __init__(self, caminho: Path, janela_em_minutos: int) -> None:
        self.caminho = Path(caminho)
        self.janela = janela_em_minutos * 60

    def _ler(self) -> dict[str, float]:
        try:
            with self.caminho.open(encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except (FileNotFoundError, json.JSONDecodeError):
            # Estado ausente ou corrompido: o aviso é mais importante que a
            # supressão. Na dúvida, avisa.
            return {}
        return dados if isinstance(dados, dict) else {}

    def pode_avisar(self, alarme: str, agora: float) -> bool:
        ultimo = self._ler().get(alarme)
        if ultimo is None:
            return True
        return (agora - ultimo) > self.janela

    def registrar(self, alarme: str, agora: float) -> None:
        dados = self._ler()
        dados[alarme] = agora
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".parcial")
        temporario.write_text(json.dumps(dados), encoding="utf-8")
        temporario.replace(self.caminho)
