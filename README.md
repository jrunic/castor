---
id: 202609131101
projeto: castor
tipo: nota
escopo: repo:castor
plataforma: "*"
status: ativo
descricao: README do repo castor — entrypoint humano.
tags: [readme, Python]
---

# castor

Toolkit para operar a própria infraestrutura pessoal: guardar segredos e
entregá-los aos serviços, manter serviço de pé, rodar rotina periódica com aviso
de falha, e manter as máquinas atualizadas.

Um comando, `castor`, com áreas de subcomandos em português. Escrito para quem
opera a própria máquina — e para o agente de IA que opera junto.

Você usa uma **máquina principal**, que guarda a chave e o cadastro, e ela
comanda as **máquinas clientes**, que executam. A cliente nunca acessa a
principal.

## Instalar

```sh
curl -fsSL https://raw.githubusercontent.com/jrunic/castor/main/scripts/instalar.sh | sh
```

Instala em `~/.local/bin/castor`. Sem Python 3.12+, o instalador põe o 3.14 no
XDG. Confere a soma do que baixou e que o comando responde depois. Se qualquer
uma falhar, ele não instala e não anuncia sucesso.

A soma pega arquivo truncado e artefato trocado sem que a soma fosse trocada
junto. Ela **não** cobre origem comprometida — arquivo e soma vêm do mesmo
lugar, e quem puder trocar um troca o outro.

## Começar

```sh
castor configurar
castor maquina preparar <nome> --endereco <endereço> --usuario-inicial <usuário>
castor maquina testar <nome>
```

`configurar` se apresenta, faz 3 perguntas (chave, nome, aviso por e-mail)
com defaults que o Enter aceita, mostra **a prévia do que vai fazer** e só
então age: instala o Tailscale se faltar e grava cadastro e cofre.
Responder `n` na prévia cancela sem fazer coisa nenhuma — nem instalar,
nem criar chave. O guia tem a sequência inteira.

O passo a passo está em
[`docs/guias/primeira-maquina.md`](docs/guias/primeira-maquina.md).

## O que existe nesta versão

| Área | Verbos | Onde roda |
|---|---|---|
| `chave` | `criar`, `usar`, `mostrar` | qualquer sistema |
| `maquina` | `preparar`, `adicionar`, `listar`, `testar`, `remover` | qualquer sistema |
| `segredos` | `gerar`, `enviar`, `estado`, `ver` | qualquer sistema |
| `servico` | `instalar`, `remover`, `estado`, `reiniciar`, `registro` | Linux |
| `rotina` | `rodar`, `agendar`, `listar` | Linux |
| `ronda` | `rodar`, `estado` | roda na principal, em qualquer sistema |
| `atualizacao` | `rodar`, `estado` | roda na principal, em qualquer sistema |

**As sete áreas estão de pé**, e cada uma lista os próprios verbos em
`castor <área> --help`.

## Três regras que o castor segue

- **Mede em vez de perguntar.** Diretório, usuário, sistema e versão vêm da
  máquina. Campo digitado é caminho errado que ninguém vai saber diagnosticar
  depois.
- **Não queima a ponte.** Toda troca de acesso estabelece o novo, **prova** o
  novo numa conexão separada, e só então desativa o antigo.
- **Não anuncia o que não conferiu.** Comando que volta zero afirma sobre o
  processo, não sobre o mundo.

## Para agentes e desenvolvedores

- `CONTEXTO.md` — padrões técnicos e restrições (comece aqui)
- `docs/` — arquitetura, decisões e documentação (Diátaxis)
- `docs/referencias/chave-e-maquina.md` — verbos, opções e códigos
  de saída

Os códigos de saída são distintos por causa: um agente distingue por código
melhor do que por prosa.
