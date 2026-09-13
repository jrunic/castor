---
id: 202609132101
projeto: castor
tipo: referencia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência das áreas chave e maquina — verbos, opções, códigos de saída e o formato do manifesto
tags: [referencia, cli, chave, maquina, manifesto]
---

# Referência: `chave` e `maquina`

## Opções globais

| Opção | Efeito |
|---|---|
| `--manifesto <caminho>` | manifesto a usar. Padrão: `$CASTOR_MANIFESTO`, ou `~/.config/castor/castor.json` |
| `--versao` | imprime a versão e sai |
| `--help` | lista as áreas; `castor <área> --help` lista os verbos |

## `castor chave`

| Verbo | O que faz |
|---|---|
| `criar [--caminho <caminho>]` | gera um par ed25519. Padrão: `~/.ssh/castor`. Recusa sobrescrever chave existente |
| `usar <caminho>` | adota uma chave que já existe. Exige a pública ao lado (`<caminho>.pub`) |
| `mostrar` | imprime a chave **pública** declarada no manifesto |

A chave privada vive no lugar padrão do sistema, não no manifesto — o manifesto
guarda só o caminho. Nenhum verbo imprime a privada.

## `castor maquina`

| Verbo | O que faz |
|---|---|
| `adicionar <nome> --endereco <endereço> [--usuario <usuário>] [--substituir]` | conecta, **mede** e cadastra uma cliente |
| `adicionar <nome> --principal` | cadastra **esta** máquina como principal |
| `preparar <nome> --endereco <endereço> --usuario-inicial <usuário> [--usuario-de-servico <usuário>]` | leva uma máquina recém-instalada a cliente |
| `listar` | uma linha por máquina: nome, papel, endereço, usuário, sistema |
| `testar <nome>` | prova a conexão e responde a versão do castor do outro lado |
| `remover <nome>` | tira do manifesto. **Não** desfaz nada na máquina |

Usuário, diretório, sistema e versão do Python nunca são digitados: vêm da
medição. O que você informa é o que é escolha sua — o nome e o endereço.

## Códigos de saída

Nenhum acumula dois sentidos. É por eles que um agente distingue o que fazer.

| Código | Significa | Providência |
|---|---|---|
| 0 | pronto | — |
| 1 | erro de uso, de manifesto ou de chave local | ler a mensagem; ela nomeia o comando que conserta |
| 2 | rede inalcançável | conferir se a máquina está ligada e o endereço certo |
| 3 | chave recusada, ou identidade do host mudada | conferir o `authorized_keys`; investigar antes de mexer no `known_hosts` |
| 4 | castor ausente do outro lado | `castor maquina preparar` |
| 5 | outro fracasso de conexão | ler o que o ssh disse, repassado na mensagem |
| 6 | expiração de chave de nó não conferida | desativar no painel e repetir |
| 7 | roteiro de preparo parado | passo sem efeito, prova faltando ou medição incompleta — a mensagem diz qual |
| 8 | algo ausente ou desatualizado | ver [`segredos-e-cofre.md`](segredos-e-cofre.md) |

## O manifesto

JSON, na máquina principal. Exemplo completo:

```json
{
  "chave": "/home/ana/.ssh/castor",
  "maquinas": {
    "bancada": {
      "papel": "principal",
      "usuario": "ana",
      "casa": "/home/ana",
      "sistema": "linux",
      "endereco": "",
      "python": "3.12.14"
    },
    "represa": {
      "papel": "cliente",
      "usuario": "castor",
      "casa": "/home/castor",
      "sistema": "linux",
      "endereco": "192.168.1.50",
      "python": "3.14.0"
    }
  }
}
```

| Campo | Origem |
|---|---|
| `papel` | `principal` ou `cliente`. Comando que escreve em cliente roda na principal |
| `usuario`, `casa`, `sistema`, `python` | **medidos** na máquina, nunca digitados |
| `endereco` | informado. Vazio na principal, que não é acessada |
| `chave` | caminho da privada, anotado por `chave criar` ou `chave usar` |

A escrita é atômica: grava ao lado e troca. Interrupção não deixa o manifesto
pela metade.

## Os passos de `preparar`

| Passo | Exige provado | Confere |
|---|---|---|
| `acesso_inicial` | — | a conexão por chave responde o usuário inicial |
| `identidade` | `acesso_inicial` | a medição voltou preenchida |
| `relogio` | — | desvio de até 120 s contra esta máquina |
| `python` | — | 3.12 ou mais novo |
| `usuario_de_servico` | — | o usuário existe |
| `provar_chave` | — | a conexão como usuário de serviço responde o nome dele |
| `sudo` | `provar_chave` | `sudo -n true` passa |
| `instalar_castor` | `provar_chave` | `castor --versao` responde |
| `rede` | `provar_chave`, `sudo` | — |
| `expiracao` | — | conduzido pelo comando, conferido na principal |
| `encerrar_acesso_inicial` | `provar_chave`, `sudo`, `instalar_castor` | **não roda nesta versão** |


Passo que declara exigência não roda sem a prova no lugar. É o mecanismo que
impede fechar um caminho de acesso antes de o novo funcionar.

Depois do roteiro, o comando cadastra a máquina e **entrega a credencial de
aviso**, se o serviço estiver declarado — ver
[`segredos-e-cofre.md`](segredos-e-cofre.md). Sem ele declarado, o comando diz
em voz alta que a máquina não sabe avisar.

## Uma limitação que vale conhecer

**Uma máquina não consegue ler a própria expiração de chave de nó.** O
`tailscale status --json` não traz esse campo para o próprio nó — só para os
outros. Por isso a conferência roda na máquina principal, olhando a cliente. Um
comando que afirmasse isso a partir da própria cliente estaria mentindo.
