import pytest


@pytest.fixture(autouse=True)
def release_sem_rede(monkeypatch):
    """Nenhum teste baixa irmão do GitHub por acidente.

    A porta 9 recusa a conexão. Quem precisa da release aponta a origem para
    um servidor local, como fazem os testes de runtime, preparar e configurar.
    """
    monkeypatch.setattr("castor.runtime.ORIGEM_DAS_RELEASES",
                        "http://127.0.0.1:9")
