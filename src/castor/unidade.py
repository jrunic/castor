"""O texto da unit systemd de um serviço declarado no manifesto.

Função pura: entra declaração, sai texto. Não toca em máquina nenhuma, e por
isso o que ela recusa se prova sem máquina nenhuma.

Unit de USUÁRIO, não de sistema: o serviço do mentorado não precisa de root. O
que precisa de root é ligar o linger, uma vez por máquina.

O arquivo de ambiente é o que a área `segredos` entrega — e é ele que mata o
wrapper que o toolkit de origem tinha só para carregar credencial antes de subir
o programa.
"""
from castor import cofre as mod_cofre

REINICIOS = ("on-failure", "always")
JANELA_DE_REINICIO = 60
TENTATIVAS_NA_JANELA = 5


class DeclaracaoInvalida(Exception):
    pass


def caminho(casa: str, nome: str) -> str:
    return f"{casa}/.config/systemd/user/{nome}.service"


def _sem_por_cento(valor: str, campo: str) -> str:
    if "%" in valor:
        raise DeclaracaoInvalida(
            f"{campo} tem '%', que o systemd lê como especificador (%h é a casa, "
            f"%i é a instância) e expande em silêncio. Tire o '%'."
        )
    return valor


def _caminho_resolvido(valor: str, *, casa: str, casa_principal: str,
                       campo: str) -> str:
    """Caminho: as duas marcas resolvem e todo o resto do cifrão é recusado."""
    return _sem_por_cento(
        mod_cofre.resolver(valor, casa=casa, casa_principal=casa_principal), campo)


def _comando_resolvido(valor: str, *, casa: str, casa_principal: str) -> str:
    """Comando: as duas marcas resolvem e o resto do cifrão PASSA.

    O systemd não expande $VAR em ExecStart — passa literal para o programa, e
    quem expande é o `sh -c` que o comando invoca, em tempo de execução, já com
    o EnvironmentFile carregado. Recusar cifrão aqui impediria um serviço de
    referenciar a própria variável de ambiente, que é para isso que a entrega
    de segredo existe.
    """
    return _sem_por_cento(
        mod_cofre.substituir_marcas(valor, casa=casa,
                                    casa_principal=casa_principal), "comando")


def montar(nome: str, declarado: dict, *, casa: str, casa_principal: str) -> str:
    comando = declarado.get("comando")
    if not comando:
        raise DeclaracaoInvalida(
            f"o serviço '{nome}' não declara 'comando' no manifesto, então não "
            f"há o que rodar. Serviço sem comando é só um conjunto de segredos."
        )
    reiniciar = declarado.get("reiniciar", "on-failure")
    if reiniciar not in REINICIOS:
        raise DeclaracaoInvalida(
            f"'reiniciar' de '{nome}' é '{reiniciar}'. Use {' ou '.join(REINICIOS)}."
        )

    comando = _comando_resolvido(comando, casa=casa, casa_principal=casa_principal)
    if not comando.startswith("/"):
        raise DeclaracaoInvalida(
            f"o comando de '{nome}' precisa de caminho absoluto: o systemd não "
            f"procura no PATH e não expande variável em ExecStart."
        )
    diretorio = _caminho_resolvido(declarado.get("diretorio", casa), casa=casa,
                                   casa_principal=casa_principal,
                                   campo="diretorio")
    ambiente = _caminho_resolvido(declarado["destino"], casa=casa,
                                  casa_principal=casa_principal, campo="destino")
    descricao = declarado.get("descricao", nome)

    return f"""[Unit]
Description={descricao}
After=network-online.target
Wants=network-online.target
# Quantas tentativas o systemd aceita na janela antes de desistir. Explícito
# porque o material é lido por agente: padrão de distribuição é número que ele
# não tem como ler daqui. Fica em [Unit] — em [Service] seria ignorado.
StartLimitIntervalSec={JANELA_DE_REINICIO}
StartLimitBurst={TENTATIVAS_NA_JANELA}

[Service]
Type=simple
WorkingDirectory={diretorio}
EnvironmentFile={ambiente}
ExecStart={comando}
Restart={reiniciar}
RestartSec=5
# 78 é EX_CONFIG: o programa disse que a própria configuração está quebrada.
# Sem esta linha ele reinicia para sempre escondendo o erro, em vez de parar e
# ser notado.
RestartPreventExitStatus=78
UMask=0077

[Install]
WantedBy=default.target
"""
