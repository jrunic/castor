---
id: 202609140500
projeto: castor
tipo: referencia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência da área ronda — os três tipos de checagem, onde cada um roda, o aviso por mudança de estado e o código de saída 10
tags: [referencia, ronda, checagem, aviso]
---

# Referência: `ronda`

Você declara o que quer vigiar; a ronda roda e diz o que está mal. Por e-mail
quando piora, e na tela quando você pergunta.

**A ronda roda na máquina principal** e distribui as próprias perguntas. A
cliente não precisa saber que ela existe — não há nada a instalar para vigiar.

## Os verbos

| Verbo | O que faz |
|---|---|
| `rodar [--ensaio]` | roda as checagens declaradas, avisa o que **mudou de estado**, e guarda o resultado |
| `estado` | mostra o resultado da última ronda, **sem reexecutar nada** |

## Os três tipos de checagem

| Tipo | Declara | Onde roda | Passou quando |
|---|---|---|---|
| `comando` | `comando` e `maquina` | na máquina, por ssh | o comando sai **zero** |
| `servico` | `servico` e `maquina` | pergunta ao systemd da máquina | está `active` |
| `expiracao` | `maquina` | **na principal** | a expiração está desativada |

```json
"ronda": {
  "janela_em_minutos": 360,
  "checagens": {
    "disco-do-computador-auxiliar": {
      "tipo": "comando",
      "maquina": "computador-auxiliar",
      "comando": "test $(df -P / | awk 'NR==2 {print $5+0}') -lt 90",
      "descricao": "disco de / abaixo de 90%"
    },
    "sentinela-de-pe": {
      "tipo": "servico", "maquina": "computador-auxiliar", "servico": "sentinela"
    },
    "computador-auxiliar-nao-expira": {"tipo": "expiracao", "maquina": "computador-auxiliar"}
  }
}
```

**Não há limiar, janela nem linha de base inventados pelo castor.** Quem declara
o que conta como "bem" é quem opera a máquina — o comando acima diz 90% porque
você escreveu 90%.

### Por que a expiração roda na principal

Uma máquina **não consegue ler a própria expiração de chave de nó**: o
`tailscale status --json` não traz esse campo para o próprio nó. Ela só é
legível na entrada de peer que as outras máquinas enxergam. Uma ronda que
afirmasse isso a partir da própria cliente estaria mentindo.

Efeito colateral útil: máquina fora do ar **não impede** essa checagem — e é
justamente quando a máquina some que saber da expiração importa.

## Quando a máquina não responde

Máquina inalcançável é **uma** falha, da máquina. As checagens dela não são
avaliadas e não viram falhas separadas. Quem recebe cinco e-mails sobre o mesmo
problema aprende a ignorar os cinco.

## O aviso

Avisa o que **mudou de estado**, não o que continua mal:

- checagem que **passou a falhar** → um e-mail, e não repete enquanto a janela
  não vencer;
- checagem que **voltou ao normal** → um e-mail, e o alarme é esquecido, para
  que uma falha nova logo depois avise de novo em vez de ficar muda.

A credencial de SMTP sai do **cofre da principal**, direto — o arquivo de
serviço com a senha é coisa da máquina cliente, e aqui não existe.

Falha no envio não derruba a ronda: o resultado sai na tela, e a falha do aviso
aparece no erro padrão.

## `--ensaio`

Roda tudo, imprime, e **não avisa nem grava**. É o que permite declarar uma
checagem nova sem disparar e-mail enquanto o comando ainda está sendo acertado.

Não gravar é de propósito: o arquivo é a linha de base da comparação, e
sobrescrevê-lo faria uma falha em curso deixar de ser avisada na ronda seguinte.

## Periodicidade

A ronda é rodada **no check-in ou à mão**. Agendar na principal depende de
`rotina agendar`, que é Linux-only nesta versão, e a principal costuma ser
macOS. Por isso o `estado` diz **há quanto tempo** foi a última: ronda velha sem
data é pior que nenhuma ronda, porque dá sensação de vigilância.

## Códigos de saída

| Código | Significa |
|---|---|
| 0 | todas as checagens passaram |
| 1 | erro de uso, de cadastro, ou checagem mal declarada |
| 2 a 5 | fracassos de conexão — ver [`chave-e-maquina.md`](chave-e-maquina.md) |
| **10** | **alguma checagem falhou** |

10 é distinto de 9 (`servico`) porque aqui ninguém tentou mudar nada: a ronda
observa.

## O que a ronda não faz

- **Não conserta.** Ela observa e avisa. Reiniciar serviço caído sozinha seria
  outra decisão.
- **Não tem severidade.** Passou ou falhou. Escalação é motor de incidentes,
  que esta versão não tem.
- **Não guarda histórico.** Só a última ronda. Série temporal é outro produto.
