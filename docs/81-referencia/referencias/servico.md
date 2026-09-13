---
id: 202609140200
projeto: castor
tipo: referencia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência da área servico — os cinco verbos, o que a unit gerada contém e por quê, o linger, e o código de saída 9
tags: [referencia, servico, systemd, unit, linger]
---

# Referência: `servico`

Deixa um programa rodando na máquina cliente e de pé depois que você desliga.
**Linux apenas** nesta versão: quem roda serviço é a cliente.

## Os verbos

| Verbo | O que faz |
|---|---|
| `instalar <servico> --maquina <nome>` | entrega o segredo, grava a unit, liga o linger, sobe o serviço e **confere que ficou ativo** |
| `remover <servico> --maquina <nome>` | para, desabilita, apaga a unit e o arquivo de segredo, e confere as duas coisas |
| `estado [--maquina <nome>]` | uma linha por serviço e máquina: ativo, habilitado, ou o que aconteceu |
| `reiniciar <servico> --maquina <nome>` | reinicia e confere que voltou. **É por aqui que um segredo trocado chega ao processo** |
| `registro <servico> --maquina <nome> [--linhas N]` | as últimas linhas que o serviço escreveu |

## O que o manifesto declara

```json
"sentinela": {
  "chaves": ["TOKEN_DA_SENTINELA"],
  "destino": "$HOME/.config/castor/sentinela.env",
  "comando": "$HOME/.local/bin/sentinela --vigiar",
  "descricao": "Sentinela da represa",
  "diretorio": "$HOME",
  "reiniciar": "on-failure",
  "maquinas": ["represa"]
}
```

| Campo | Para quê |
|---|---|
| `comando` | o que roda. Sem ele, a declaração é só um conjunto de segredos, e `instalar` recusa |
| `descricao` | vai para `Description=` |
| `diretorio` | `WorkingDirectory=`. Sem ele, a casa da máquina |
| `reiniciar` | `on-failure` (padrão) ou `always` |

Os campos `chaves` e `destino` são os mesmos da área `segredos` — um serviço é
uma declaração só, usada pelas duas áreas.

### Cifrão: proibido no caminho, permitido no comando

Em `diretorio` e `destino`, que são caminhos, vale a regra do cofre: as duas
marcas resolvem e qualquer outro cifrão é recusado.

Em `comando`, **o cifrão passa**. O systemd não expande `$VAR` em `ExecStart` —
entrega literal ao programa, e quem expande é o `sh -c` que o próprio comando
invoca, já com o arquivo de ambiente carregado. É assim que um serviço usa o
segredo que o castor entregou:

```json
"comando": "/bin/sh -c 'meu-programa --token $TOKEN_DA_SENTINELA'"
```

### `%` é recusado nos três

Em unit do systemd, `%h` e `%i` são especificadores e expandem em silêncio. Um
`%` que você pôs achando que era literal vira outra coisa.

## A unit gerada, linha a linha

```ini
[Unit]
Description=Sentinela da represa
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=/home/castor
EnvironmentFile=/home/castor/.config/castor/sentinela.env
ExecStart=/home/castor/.local/bin/sentinela --vigiar
Restart=on-failure
RestartSec=5
RestartPreventExitStatus=78
UMask=0077

[Install]
WantedBy=default.target
```

| Linha | Por quê |
|---|---|
| `StartLimit*` em `[Unit]` | é onde a diretiva vale desde o systemd 229. Em `[Service]` ela é **ignorada em silêncio** |
| `EnvironmentFile=` | o arquivo que a área `segredos` entrega. É ele que dispensa o wrapper de shell que outros toolkits usam só para carregar credencial |
| `RestartPreventExitStatus=78` | 78 é `EX_CONFIG`: o programa disse que a própria configuração está quebrada. Sem esta linha ele reinicia para sempre escondendo o erro, em vez de parar e ser notado |
| `UMask=0077` | o que o serviço criar nasce só para o dono |
| `WantedBy=default.target` | unit de **usuário**, não de sistema — o serviço não precisa de root |

## O linger

Unit de usuário roda sob um gerenciador que, por padrão, **morre com a última
sessão** — e leva o serviço junto. O linger é o que faz esse gerenciador ficar
de pé sem ninguém logado.

- `instalar` liga o linger com `sudo` e **confere** (`loginctl show-user` →
  `Linger=yes`). Se não pegou, não anuncia instalação.
- **Isto muda a máquina além do castor:** o usuário passa a ter processos de pé
  sem sessão aberta.
- `remover` **não** desliga o linger. Ele pode estar sustentando outro serviço, e
  desligá-lo exigiria contar quantos restam — contagem errada derruba serviço
  alheio. O comando diz que ficou.

## Códigos de saída

| Código | Significa |
|---|---|
| 0 | pronto, ou tudo ativo |
| 1 | erro de uso, de manifesto, ou declaração de serviço inválida |
| 2, 3, 4, 5 | fracassos de conexão — ver [`chave-e-maquina.md`](chave-e-maquina.md) |
| **9** | **o serviço não ficou ativo, não parou, ou um comando de systemd falhou** |

9 é distinto de 5 de propósito: em 5 a conexão falhou; em 9 a conexão funcionou
e o mundo é que não mudou.

## Trocar um segredo de serviço que já roda

```sh
# editou o cofre
castor segredos enviar sentinela --maquina represa
castor servico reiniciar sentinela --maquina represa
```

`segredos estado` afirma sobre o **arquivo**; o processo em memória só vê o
valor novo depois do `reiniciar`.
