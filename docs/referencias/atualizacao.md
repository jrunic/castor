---
id: 202609140700
projeto: castor
tipo: referencia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência da área atualizacao — os quatro tipos de alvo, a ordem de execução, o que a atualização confere e o que esta versão não tem
tags: [referencia, atualizacao, pipx, npm, release]
---

# Referência: `atualizacao`

Mantém em dia o que você declarou — e o próprio castor — nas duas máquinas, com
um comando dado na principal.

## Os verbos

| Verbo | O que faz |
|---|---|
| `rodar [--seco]` | atualiza os alvos declarados e **confere que o comando ainda responde** |
| `estado` | diz que versão está em cada máquina, **sem atualizar nada** |

## Os quatro tipos de alvo

| Tipo | Declara | Como atualiza |
|---|---|---|
| `castor` | só as máquinas | roda o instalador de bootstrap, que **confere a soma publicada** |
| `pipx` | `pacote` | `pipx upgrade <pacote>` |
| `npm` | `pacote` | `npm update -g <pacote>` |
| `comando` | `comando` | roda o que você declarou |

```json
"atualizacao": {
  "alvos": {
    "castor": {"tipo": "castor", "maquinas": ["bancada", "represa"]},
    "jd-exemplo": {
      "tipo": "pipx",
      "pacote": "git+https://github.com/exemplo/jd-exemplo.git",
      "maquinas": ["represa"],
      "versao": "jd-exemplo --version",
      "reiniciar": "sentinela"
    }
  }
}
```

| Campo | Para quê |
|---|---|
| `versao` | como perguntar a versão. Sem ele, a conferência é se o comando **responde** |
| `reiniciar` | serviço a reiniciar quando a versão muda — ver [`servico.md`](servico.md) |
| `maquinas` | onde aquele alvo existe |

## A ordem, e por que ela é essa

1. Todos os alvos que não são o castor.
2. O castor das clientes.
3. **O castor da principal, por último de tudo.**

Um castor novo quebrado não pode derrubar uma rodada que já estava andando, e o
relatório precisa dizer o que já tinha sido feito. Na principal, o processo em
execução continua com o código velho em memória até a próxima invocação — isso
é normal.

**A principal se atualiza localmente**, sem ssh: não há caminho de volta para
ela, e nem deve haver. É a metade macOS do que esta área faz.

## O que cada atualização confere

A versão é perguntada **antes e depois**. Três desfechos:

| Relatório | Significa |
|---|---|
| `1.0 → 1.1` | atualizou |
| `sem mudança` | já estava em dia — **não é falha** |
| `não respondeu depois da atualização` | **falha**: o gerenciador saiu zero e o comando quebrou |

Conferir só que o `pipx` ou o `npm` saiu zero não prova que o programa roda. É a
diferença entre afirmar sobre o processo e afirmar sobre o mundo.

### O que "sem mudança" não afirma

Ele diz que **a versão não mudou** — não que você está na última. São coisas
diferentes, e a distância entre elas aparece em pelo menos três situações:

- o artefato publicado ainda não propagou na borda que serve aquela máquina
  (medido em 13/09/2026, minutos depois de publicar uma release: uma máquina
  atualizou e a outra recebeu o artefato antigo, e as duas saíram "ok");
- o pacote saiu do índice de onde era instalado;
- a origem responde, mas com a versão de antes.

Nos três, o relatório está tecnicamente certo e a leitura apressada está errada.
Quando a atualização importa — logo depois de uma release, por exemplo —
**confira a versão com `castor atualizacao estado`** em vez de ler o "ok" da
rodada.

## `--seco`

Mostra o comando que rodaria em cada máquina, e não roda nada.

## Códigos de saída

| Código | Significa |
|---|---|
| 0 | tudo em dia ou atualizado |
| 1 | erro de uso, de manifesto, ou alvo mal declarado |
| 2 a 5 | fracassos de conexão — ver [`chave-e-maquina.md`](chave-e-maquina.md) |
| **11** | **algum alvo não atualizou ou ficou sem responder** |

## O que esta versão não tem, dito em voz alta

- **Sem idade mínima.** `pipx upgrade` de um pacote instalado de um git remoto
  traz o que estiver na ponta, do jeito que estiver.
- **Sem confiança nem aprovação.** Não há "esta versão precisa de aval" nem
  "espere N dias antes de adotar". Quem roda, adota.
- **Sem rollback.** Atualizou e quebrou, volta-se à mão. Guardar o artefato
  anterior para desfazer é outra fatia.
- **Sem agendamento na principal.** `rotina agendar` é Linux-only nesta versão;
  na principal, a atualização é manual ou feita no check-in.

Isso está escrito porque um material que cala sobre governança deixa quem lê
supor que ela existe.
