---
id: 202609140800
projeto: castor
tipo: referencia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência da área rotina — o que roda sozinho na máquina cliente, com trava, teto de tempo, registro e aviso de falha uma vez por janela
tags: [referencia, rotina, cron, aviso]
---

# Referência: `rotina`

Faz um comando rodar sozinho, de tempos em tempos, **na máquina cliente**, e
avisar por e-mail quando falhar.

**É a única parte do castor que funciona sem ninguém dar comando nenhum.** A
`ronda` é rodada por você, da principal; a rotina roda pelo agendador da própria
cliente. Se o que você quer é "me avise se quebrar, sem eu ter que lembrar", é
aqui.

**Linux apenas** nesta versão: o agendador é o `cron` da cliente.

## Os verbos

| Verbo | Onde roda | O que faz |
|---|---|---|
| `rodar <nome> --maquina <nome-da-maquina>` | **na cliente** | executa a rotina com trava, teto de tempo, registro e aviso de falha |
| `agendar <nome> --maquina <nome-da-maquina>` | **na cliente** | põe (ou substitui) a linha dela no `crontab` |
| `listar` | **na cliente** | mostra as rotinas do castor que estão no `crontab` |

Os três são comandos que a **cliente** dá a si mesma — quem os chama é o `cron`
dela, ou você por uma sessão de ssh nela. Não há verbo da principal que agende
na cliente nesta versão: você entra na máquina uma vez, agenda, e não volta.

## O que o manifesto declara

```json
"rotinas": {
  "limpeza": {
    "quando": "0 3 * * *",
    "comando": "/home/castor/bin/limpar-temporarios",
    "teto_em_segundos": 900,
    "maquina": "represa"
  }
}
```

| Campo | Para quê |
|---|---|
| `quando` | os cinco campos do `cron` |
| `comando` | o que executar. Caminho absoluto — o `cron` tem PATH curto |
| `teto_em_segundos` | tempo máximo. Estourou, a rotina morre com código **124** |
| `maquina` | **de quem é a rotina.** É por este campo que ela chega na cliente, dentro do manifesto-da-cliente |

Sem `maquina`, a rotina não vai para máquina nenhuma — o manifesto-da-cliente
filtra por ele. Veja
[`segredos-e-cofre.md`](segredos-e-cofre.md#o-manifesto-da-cliente).

## O que `rodar` garante

| Garantia | Como |
|---|---|
| **Não empilha** | trava de arquivo não-bloqueante: se a execução anterior ainda está rodando, a nova desiste em silêncio e sai **0** |
| **Não trava para sempre** | `teto_em_segundos` mata o comando e devolve **124** |
| **Deixa rastro** | a saída (padrão e de erro) vai para `$CASTOR_ESTADO/registros/<nome>.log` |
| **Avisa quando falha** | um e-mail por alarme por janela |
| **O código de saída é o do comando** | o castor não o substitui — e falha no envio do aviso **não** o engole |

O estado fica em `$CASTOR_ESTADO`, que por padrão é
`~/.local/state/castor`: os registros, as travas e o arquivo de avisos já
enviados.

## O aviso

Vem da configuração `aviso` do manifesto-da-cliente, e a senha sai do **arquivo
de serviço que a área `segredos` entregou nessa máquina** — não do cofre, que
nunca sai da principal.

```json
"aviso": {
  "servidor": "smtp.exemplo.test",
  "porta": 587,
  "usuario": "castor@exemplo.test",
  "de": "castor@exemplo.test",
  "para": "voce@exemplo.test",
  "janela_em_minutos": 60,
  "arquivo_de_segredo": "$HOME/.config/castor/correio.env",
  "variavel": "SMTP_SENHA"
}
```

**Sem essa configuração no lugar, a rotina roda, falha e ninguém fica sabendo** —
e o comando diz isso em voz alta no erro padrão, em vez de silenciar.

A supressão é por alarme e por janela: a mesma rotina falhando de hora em hora
manda **um** e-mail por janela, não um por execução.

## Pôr uma rotina para rodar, do começo ao fim

Na principal, declare a rotina e entregue o manifesto atualizado à cliente:

```sh
# 1. declare "rotinas" no manifesto (edição à mão — não há verbo que escreva)
# 2. entregue: todo 'enviar' atualiza o manifesto-da-cliente junto
castor segredos enviar correio --maquina represa
```

Na cliente, uma única vez:

```sh
ssh castor@<endereço>
castor rotina agendar limpeza --maquina represa
castor rotina listar
```

A partir daí ela roda sozinha. Para ver o que aconteceu:

```sh
cat ~/.local/state/castor/registros/limpeza.log
```

## O que o `agendar` não faz

Ele **nunca reescreve linha que não seja do castor**. Cada linha que ele põe
termina com uma marca `# castor:<nome>`, e é só nas linhas com essa marca que
ele mexe. O `crontab` é seu; o castor ocupa as linhas dele e nada mais.

Reagendar a mesma rotina substitui a linha dela. Não há verbo para
desagendar nesta versão — apague a linha marcada com `crontab -e`.

## Códigos de saída

| Código | Significa |
|---|---|
| 0 | o comando saiu 0, **ou** não rodou porque já havia uma execução em curso |
| 1 | rotina não declarada no manifesto, ou erro de manifesto |
| **124** | o teto de tempo estourou |
| qualquer outro | é o código do próprio comando, repassado |

## O que esta versão não tem

- **Agendamento a partir da principal.** Você entra na cliente uma vez para
  agendar. Agendar de fora exigiria escrever no `crontab` remoto, e isso é
  fatia própria.
- **macOS.** O agendador aqui é o `cron`; `launchd` é outra fatia.
- **Desagendar.** `crontab -e` e apagar a linha marcada.
- **Prova automatizada de que o e-mail sai.** O caminho inteiro é testado com
  um remetente de mentira; provar o envio real exigiria um servidor de verdade.
