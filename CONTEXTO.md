---
id: 202609131101
projeto: castor
tipo: index
escopo: repo:castor
plataforma: "*"
status: ativo
descricao: Padrões técnicos canônicos e restrições do repo castor — carga default da sessão.
tags: [contexto, dev-skills, python]
---

# CONTEXTO.md — castor

## Onde o trabalho acontece

**O trabalho de desenvolvimento acontece fora deste repositório**, nos
documentos internos do autor.

| Artefato | Lar canônico |
|---|---|
| Roadmap de ciclos, spec, plano | fora deste repositório |
| Arquivo de apoio de tarefa, diário de sessão | fora deste repositório |
| Discussão de negócio | fora deste repositório |
| **Código, testes, migrations** | **este repositório** |
| **Documentação do produto** (Diátaxis) | **este repositório**, `docs/` |
| **ADR de contrato** | **este repositório**, `docs/decisoes/` |
| **Modelo de domínio** | **este repositório**, `docs/dominio/` |
| **README, CHANGELOG, GLOSSARIO, CONTEXTO** | **este repositório**, raiz |

**Razão:** spec, plano, roadmap e diário nomeiam contexto que não pertence a um
repositório aberto. O repositório carrega o que a audiência dele precisa.

**As skills leem esta seção** em vez de inferir por visibilidade.

## Propósito

Toolkit de infra pessoal: guardar segredos e entregá-los aos serviços, manter
serviço de pé, rodar rotina periódica com aviso de falha, e manter a máquina
atualizada. Um comando, `castor`, com áreas de subcomandos em português.

Para quem: quem opera a própria máquina — e o agente de IA que opera junto.

## Agente padrão

**Tech** — guardião deste repositório.

## Stack

- **Linguagem:** Python 3.12+ (**stdlib-only** em runtime; sem código nativo)
- **CLI:** `argparse` (stdlib)
- **Cadastro:** JSON (stdlib — sem dependência de interpretador externo)
- **Testes:** pytest
- **Distribuição:** aplicação Python de arquivo único, publicada como release
  no GitHub. **Não** publica em registro de pacote.
- **Instalação:** script de bootstrap em shell (`instalar.sh`, teto 130
  linhas) e irmão `instalar-python.sh` (teto 80) quando não há Python ≥3.12.
  O teto existe para o shell não virar programa.

## Padrões técnicos

### Naming

- **Arquivos e pastas:** kebab-case (`.py` em snake_case, por PEP 8)
- **Funções e variáveis:** snake_case · **Classes:** PascalCase ·
  **Constantes:** UPPER_SNAKE

### Linguagem

- **Subcomandos da CLI:** pt-BR (`castor segredos enviar`)
- **Identificadores no código:** **pt-BR** — divergência consciente do default
  da stack, registrada em "Decisões locais divergentes"
- **Comentários e saída para humano:** pt-BR
- **Commits:** tipo conventional em inglês (`feat`, `fix`, `docs`, `chore`,
  `refactor`), assunto em pt-BR

### Segredos

O produto gerencia os segredos **do usuário**; o repositório não contém
segredo nenhum, nem em fixture, nem em teste. O formato do arquivo gerado é
estrito, uma atribuição por linha — consumível como `EnvironmentFile` de unit
systemd **e** por `source` em shell.

### Bibliotecas

- **Política: stdlib primeiro.** Biblioteca externa exige ADR local.
- **Zero código nativo** — restrição-âncora da distribuição de arquivo único.

### Estrutura

```
CONTEXTO.md GLOSSARIO.md — contratos vivos (raiz)
src/castor/       — pacote da aplicação
tests/            — pytest
91-diario/        — diários de sessão
docs/decisoes/  — ADRs locais
docs/{tutoriais,guias,referencias,explicacoes}/ — Diátaxis
```

### Build/Run

- **Preparo:** `python3.12 -m venv .venv && .venv/bin/pip install pytest`
- **Testes:** `.venv/bin/pytest`
- **Run (desenvolvimento):** `python -m castor` a partir de `src/`
- **Empacotar:** `python scripts/build-pyz.py`

## Leitura obrigatória antes de spec/plano

- `docs/arquitetura.md` — mapa estrutural
- `GLOSSARIO.md` — vocabulário do domínio (usar estes termos, nunca sinônimos)
- `docs/dominio/` — modelo formal dos contextos que o trabalho toca

## Restrições

- **Simplicidade vence capacidade.** A audiência é alguém com pouca
  experiência em tecnologia operando a própria máquina. Mecanismo que exige um
  conceito novo do usuário precisa justificar o conceito — e a régua é se a
  pessoa consegue explicar o que fez para outra pessoa. Foi esta regra que
  derrubou o modelo de provedor e template herdado do toolkit de origem, em
  favor de um arquivo único de `CHAVE=valor`.
- **O comando mede em vez de perguntar.** Diretório, usuário, sistema e versão
  vêm da máquina, por medição, não de resposta digitada. Cada campo que o
  usuário digita é um caminho errado que ninguém vai saber diagnosticar depois.
- **Ordem que não queima a ponte.** Toda troca de acesso — chave, usuário,
  rede, porta — estabelece o novo, **prova** o novo numa conexão separada, e só
  então desativa o antigo. Enquanto a prova não passar, a desativação não
  acontece.
- **Repositório público não nomeia a árvore interna do autor** — nem em
  documento, nem em comentário, nem em mensagem de commit. Sem caminho
  absoluto, sem nome de cliente, sem nome de pessoa real. Varredura antes de
  todo push.
- **Todo dado de exemplo é sintético.** Nome de máquina, de usuário e de
  serviço em fixture, doc ou teste é inventado.
- **Nenhum comando imprime valor de segredo na saída padrão por default.**
  Quem precisa conferir recebe comprimento e soma de verificação; o valor só
  sob flag explícita.
- **Nada do host do usuário é cravado no código.** Máquina, usuário, diretório
  e caminho vêm do cadastro. Código com nome de host embutido é defeito, não
  configuração — foi o que travou a reutilização do toolkit de origem.
- **Stdlib primeiro** (acima), e **zero código nativo**.
- **Runner de testes canônico:** `.venv/bin/pytest` na raiz. O `python3` de
  sistema do macOS é 3.9 e não serve — o ambiente nasce de um Python 3.12+.
- Implementação que contradiz `docs/dominio/` ou `GLOSSARIO.md`
  atualiza o doc no mesmo commit.

## Decisões locais divergentes

- **Identificadores de código em pt-BR**, em vez do inglês que a convenção da
  linguagem sugere. Motivo: a audiência que lê e opera este código é
  lusófona — o usuário e o agente de IA dele —, e a CLI já expõe subcomandos
  em português. Precedente na mesma família de produto.

## Estado atual

**As sete áreas de pé**, mais `castor configurar` na raiz. Superfície: cadastro
(`--cadastro`, `CASTOR_CADASTRO`), `--ensaio`. Sem Python ≥3.12 o instalador
põe 3.14 no XDG data. Última release publicada: **0.2.0**. Toda mudança de
comportamento entra no `CHANGELOG.md` no mesmo commit.

Antes de aceitar o ciclo `configurar-principal`: medir `castor configurar`
nesta máquina. O download do 3.14 contra o GitHub não passou pela suíte.

## Referências

- `docs/arquitetura.md` — mapa estrutural (carga sob demanda)
- `docs/explicacoes/visao-geral.md` — o quê e por quê
- `docs/guias/primeira-maquina.md` — pôr a primeira cliente de pé
- `docs/referencias/chave-e-maquina.md` — verbos, códigos de saída, cadastro
- `docs/referencias/segredos-e-cofre.md` — o cofre, as marcas, a entrega
- `docs/referencias/servico.md` — a unit gerada, o linger, o código 9
- `docs/referencias/rotina.md` — o que roda sozinho na cliente
- `docs/referencias/ronda.md` — os três tipos de checagem, o código 10
- `docs/referencias/atualizacao.md` — os alvos, a ordem, o código 11
- `docs/decisoes/` — ADRs locais
