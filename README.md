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

Você usa uma **máquina principal**, que guarda a chave e o manifesto, e ela
comanda as **máquinas clientes**, que executam. A cliente nunca acessa a
principal.

## Instalar

Precisa de Python 3.12 ou mais novo.

```sh
curl -fsSL https://raw.githubusercontent.com/jrunic/castor/main/scripts/instalar.sh | sh
```

Instala em `~/.local/bin/castor`. O instalador confere a versão do Python antes
e confere que o comando responde depois — se qualquer uma das duas falhar, ele
não anuncia sucesso.

## Começar

```sh
castor chave criar                          # a chave de acesso às clientes
castor maquina adicionar <nome> --principal # esta máquina
castor maquina preparar <nome> --endereco <endereço> --usuario-inicial <usuário>
castor maquina testar <nome>
```

O passo a passo está em
[`docs/81-referencia/guias/primeira-maquina.md`](docs/81-referencia/guias/primeira-maquina.md).

## O que existe nesta versão

| Área | Verbos | Onde roda |
|---|---|---|
| `chave` | `criar`, `usar`, `mostrar` | qualquer sistema |
| `maquina` | `preparar`, `adicionar`, `listar`, `testar`, `remover` | qualquer sistema |
| `rotina` | `rodar`, `agendar`, `listar` | Linux |
| `segredos` | `gerar`, `ver` | qualquer sistema |

`servico`, `ronda` e `atualizacao` aparecem em `castor --help` e ainda não têm
verbos. A área `segredos` está em modelo antigo e vai mudar — veja o
`CONTEXTO.md` antes de usá-la.

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
- `docs/81-referencia/` — arquitetura, decisões e documentação (Diátaxis)
- `docs/81-referencia/referencias/chave-e-maquina.md` — verbos, opções e códigos
  de saída

Os códigos de saída são distintos por causa: um agente distingue por código
melhor do que por prosa.
