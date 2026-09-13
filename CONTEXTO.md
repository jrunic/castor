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

Este repositório é **público**. Spec, plano, roadmap e material operacional
**não vivem aqui** — ficam em documentos internos do autor, fora deste
repositório. Aqui ficam código, testes, documentação de produto e ADRs de
contrato, escritos para a audiência externa.

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
- **Manifesto:** JSON (stdlib — sem dependência de interpretador externo)
- **Testes:** pytest
- **Distribuição:** aplicação Python de arquivo único, publicada como release
  no GitHub. **Não** publica em registro de pacote.
- **Instalação:** script de bootstrap em shell — o único shell do produto,
  mantido abaixo de cem linhas.

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
docs/81-referencia/decisoes/  — ADRs locais
docs/81-referencia/{tutoriais,guias,referencias,explicacoes}/ — Diátaxis
```

### Build/Run

- **Testes:** `pytest`
- **Run (desenvolvimento):** `python -m castor`

## Leitura obrigatória antes de spec/plano

- `docs/81-referencia/arquitetura.md` — mapa estrutural
- `GLOSSARIO.md` — vocabulário do domínio (usar estes termos, nunca sinônimos)
- `docs/81-referencia/dominio/` — modelo formal dos contextos que o trabalho toca

## Restrições

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
  e caminho vêm do manifesto. Código com nome de host embutido é defeito, não
  configuração — foi o que travou a reutilização do toolkit de origem.
- **Stdlib primeiro** (acima), e **zero código nativo**.
- **Runner de testes canônico:** `pytest` na raiz do repositório.
- Implementação que contradiz `docs/81-referencia/dominio/` ou `GLOSSARIO.md`
  atualiza o doc no mesmo commit.

## Decisões locais divergentes

- **Identificadores de código em pt-BR**, em vez do inglês que a convenção da
  linguagem sugere. Motivo: a audiência que lê e opera este código é
  lusófona — o usuário e o agente de IA dele —, e a CLI já expõe subcomandos
  em português. Precedente na mesma família de produto.

## Estado atual

Repositório criado em 2026-09-13. Primeira fatia especificada e aprovada;
implementação ainda não começou.

## Referências

- `docs/81-referencia/arquitetura.md` — mapa estrutural (carga sob demanda)
- `docs/81-referencia/explicacoes/visao-geral.md` — o quê e por quê
- `docs/81-referencia/decisoes/` — ADRs locais
