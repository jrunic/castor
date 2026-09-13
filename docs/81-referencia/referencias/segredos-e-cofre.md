---
id: 202609132330
projeto: castor
tipo: referencia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência da área segredos — o cofre, as duas marcas, os quatro verbos, o manifesto-da-cliente e os códigos de saída
tags: [referencia, segredos, cofre, entrega]
---

# Referência: `segredos` e o cofre

## O cofre

Um arquivo na máquina principal, uma atribuição por linha:

```
# linhas em branco e comentários são ignorados
SMTP_SERVIDOR=smtp.exemplo.test
SMTP_PORTA=587
SMTP_SENHA="abacaxi-de-mentira-123"
```

| Regra | Por quê |
|---|---|
| Permissão `600` | cofre legível por outro usuário não é cofre — o comando **recusa** e diz o `chmod` |
| Fica só na principal | nenhum comando copia o cofre para outra máquina |
| Ninguém escreve nele pelo castor | é um arquivo que você edita; não há verbo que grave |
| Caminho declarado no manifesto | chave `cofre` |

**O compromisso, declarado:** um arquivo concentra tudo, e o raio de dano é
maior que o de segredos separados por serviço. Para uma pessoa com duas máquinas
é a troca certa; para uma frota não seria. O que compensa é a filtragem — cada
serviço recebe só as chaves declaradas para ele.

## As duas marcas

| Marca | Vira |
|---|---|
| `$HOME` | o diretório da máquina **que vai usar o arquivo** |
| `$HOME_PRINCIPAL` | o diretório da máquina principal |

São as duas únicas, nuas (sem `${}`), resolvidas na geração a partir do que o
cadastro **mediu**. Depois de resolver, qualquer cifrão ou crase que sobre é
recusado: o shell expande, o systemd lê literal, e os dois consumidores
divergiriam. `$HOMEX` não é marca.

Valem tanto nos valores do cofre quanto nos caminhos de destino.

## Os verbos

| Verbo | O que faz |
|---|---|
| `gerar <servico> --maquina <nome> --destino <arquivo>` | filtra o cofre, resolve, e **grava em arquivo**. Sem `--destino`, recusa |
| `enviar <servico> --maquina <nome>` | entrega o arquivo do serviço à cliente **e atualiza o manifesto-da-cliente** |
| `estado` | por serviço e máquina: em dia, desatualizado, ausente ou inalcançável |
| `ver <arquivo> <variavel> [--revelar]` | descreve a variável (tamanho e soma); só revela sob pedido |

**A disciplina que o material carrega:** `gerar` redireciona para arquivo, `ver`
descreve por default, e nada aqui ensina a imprimir valor de segredo no
terminal. O que `estado` imprime é nome, situação e soma — nunca valor.

## Como o segredo atravessa

Pela entrada padrão do `ssh`. Do outro lado, `umask 077`, grava ao lado e troca.
Não há arquivo temporário na cliente para alguém ler no meio do caminho, e o
conteúdo nunca vira argumento de comando — argumento aparece na lista de
processos da máquina.

## O que entra no manifesto

```json
{
  "cofre": "/home/ana/.config/castor/cofre",
  "servicos": {
    "correio": {
      "chaves": ["SMTP_SERVIDOR", "SMTP_PORTA", "SMTP_USUARIO", "SMTP_SENHA"],
      "destino": "$HOME/.config/castor/correio.env",
      "maquinas": ["represa"]
    }
  },
  "aviso": {
    "servico": "correio",
    "servidor": "smtp.exemplo.test", "porta": 587,
    "usuario": "castor@exemplo.test", "de": "castor@exemplo.test",
    "para": "ana@exemplo.test", "janela_em_minutos": 60,
    "arquivo_de_segredo": "$HOME/.config/castor/correio.env",
    "variavel": "SMTP_SENHA"
  },
  "rotinas": {
    "limpeza": {"quando": "0 3 * * *", "comando": "true", "maquina": "represa"}
  }
}
```

| Campo | Para quê |
|---|---|
| `servicos.<nome>.chaves` | o que aquele serviço recebe do cofre, e nada além |
| `servicos.<nome>.destino` | onde o arquivo fica na máquina que o usa |
| `servicos.<nome>.maquinas` | quem recebe. Sem ele, `estado` olha todas as clientes |
| `aviso.servico` | qual serviço carrega a credencial de SMTP. Sem ele, `correio` |
| `rotinas.<nome>.maquina` | de quem é a rotina — **é por ele que ela chega na cliente** |

## O manifesto-da-cliente

O manifesto inteiro mora na principal e **não** é copiado. A cliente recebe, em
`~/.config/castor/castor.json`, só o que diz respeito a ela: o próprio cadastro,
suas rotinas, sua ronda e a configuração de aviso, com os caminhos já
resolvidos. Vai junto de todo `enviar`.

**Não vão:** o cofre, a chave de acesso, as outras máquinas, e o endereço da
principal — a cliente não acessa a principal, e endereço ali seria convite.

## Códigos de saída

| Código | Significa |
|---|---|
| 0 | pronto, ou tudo em dia |
| 1 | erro de uso, de manifesto ou de cofre (ausente, frouxo, chave faltando) |
| 2 | rede inalcançável |
| 3 | chave recusada |
| 4 | castor ausente do outro lado |
| 5 | outro fracasso de conexão, inclusive falha ao gravar na cliente |
| 6 | expiração de chave de nó não conferida |
| 7 | roteiro de preparo parado |
| **8** | **algo ausente ou desatualizado** (`estado`) |

## Uma coisa que `estado` não afirma

Ele compara **arquivos**, não processos. Um serviço que já estava rodando
continua com o valor antigo em memória depois de o arquivo ser trocado — e o
`estado` vai dizer "em dia", corretamente, porque o arquivo está certo.

Quem leva o valor novo ao processo é
[`castor servico reiniciar`](servico.md):

```sh
castor segredos enviar sentinela --maquina represa
castor servico reiniciar sentinela --maquina represa
```
