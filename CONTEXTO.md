---
id: 202609131101
projeto: castor
tipo: index
escopo: repo:castor
plataforma: "*"
status: ativo
descricao: Padrões técnicos canônicos e restrições do repo castor — carga default da sessão.
tags: [contexto, dev-skills, Python]
---

# CONTEXTO.md — castor

## Propósito

[A ser preenchido pela primeira spec via dev-02-escreve-spec.]

## Agente padrão

**Tech** (SRE Agentic) — guardião deste repositório. Modo de atuação: Código + SRE Agentic
(Autocura Assistida). Outros agentes podem ler/contribuir; mudanças estruturais passam por Tech.

## Stack

- **Linguagem:** Python
- **Framework:** [a definir]
- **Banco:** [a definir]
- **Deploy:** [a definir]

## Padrões Técnicos

### Naming

[Preenchido pela skill dev-01-define-padroes conforme convenção da stack.
Ver PADROES-COMUNIDADE.md da skill para tabela completa.]

### Linguagem

- **Slug do repo/CLI:** pt-BR (`jedi-<slug>`, `jd-<slug>`)
- **Identificadores no código:** convenção da stack (inglês para Python/JS/Go)
- **Comentários inline:** pt-BR
- **Commits:** tipo conventional em inglês (`feat:`, `fix:`...), descrição em pt-BR

### Segredos

- **Onde:** [jedi-secrets / .env local / GCP Secret Manager / ...]
- **Convenção de nomes:** [definir]

### Bibliotecas

- **Política:** [livre / requer ADR / lista permitida]
- **Atuais:** [lista inicial]

### Estrutura

```
CONTEXTO.md GLOSSARIO.md roadmap.md — contratos vivos (raiz)
91-diario/        — diários de sessão
docs/11-tarefas/  — specs e planos datados
docs/12-issues/   — bugs e demandas isoladas (AAAAMMDD-<slug>.md, estado no frontmatter)
docs/81-referencia/decisoes/  — ADRs locais
docs/81-referencia/dominio/   — modelo de domínio (neg-02)
docs/81-referencia/{tutoriais,guias,referencias,explicacoes}/ — quadrantes Diátaxis (ADR 20260620)
```

### Testes

- **Framework:** [a definir]
- **Pasta:** `tests/`

### Build/Run

- **Setup:** [comando]
- **Testes:** [comando]
- **Run:** [comando]
- **Build:** [comando]

### Lint/Format

- **Lint:** [comando]
- **Format:** [comando]

## Onde o trabalho acontece

Este repositório é **público**. Spec, plano, roadmap e material
operacional **não vivem aqui** — ficam em documentos internos do autor, fora
deste repositório. Aqui ficam código, testes, documentação de produto e ADRs de
contrato, escritos para a audiência externa.

## Leitura obrigatória antes de spec/plano

- `docs/81-referencia/arquitetura.md` — mapa estrutural
- `GLOSSARIO.md` — vocabulário do domínio (usar estes termos, nunca sinônimos)
- `roadmap.md` — incremento ativo e fronteiras (contrato do Passo 0 do dev-02)
- `docs/81-referencia/dominio/` — modelo formal dos contextos que o trabalho toca

## Restrições

Hard limits sempre relevantes durante a sessão (ADR `20260609-eliminacao-do-84-ia.md` — substitui antigo `docs/84-ia/restricoes.md`).

- **Runner de testes canônico:** [comando — ex: `.venv/bin/pytest`]
- **Idioma da saída para humano:** pt-BR
- **Comentários inline:** pt-BR
- **Slug do repo/CLI:** pt-BR (`jedi-<slug>`, `jd-<slug>`)
- **Implementação que contradiz `docs/81-referencia/dominio/` ou `GLOSSARIO.md` atualiza o doc no mesmo commit;** divergência que vira decisão arquitetural → dev-07-cria-adr (ADR `20260705-familia-neg-skills-negocio`)
- [Instanciar por CÓPIA as Restrições do documento de padrões da classe de app, quando houver — herança explícita]
- [Adicionar regras com histórico ou alto custo de violar — não documentar o óbvio]

## Decisões Herdadas (explícitas)

Repetidas aqui mesmo presentes em AMBIENTE.md / USUARIO.md / AGENTE.md, para evitar herança implícita:

- Kebab-case em paths + comentários em pt-BR (AMBIENTE.md global)
- Python 3.12 / Node 22 LTS pinados; sem `.python-version` ou `.nvmrc` (ADR `20260511-versoes-fixas-runtime-frota`)
- Segredos OAuth em jedi-secrets (ADR `20260510-oauth2-google-credenciais-infra-jedi-secrets`)
- Sem comandos git destrutivos sem confirmação; hook `dev-20-bloqueia-comandos-perigosos` em produção
- Ferramentas canônicas vencem APIs diretas (ADR `ferramentas-canonicas.md`)
- Padrão Ação Documentada para destrutivos (ADR `padrao-acao-documentada.md`)
- Infra genérica antes do tenant específico (ADR `infra-generica-antes-do-tenant-especifico.md`)
- Conhecimento destilado em `docs/81-referencia/`; restrições em `CONTEXTO.md` (ADR `20260609-eliminacao-do-84-ia.md`)

## Decisões Locais Divergentes

[Listar onde este projeto diverge de regras globais. Cada divergência idealmente tem ADR em docs/81-referencia/decisoes/.]

## Estado Atual

Projeto criado em 2026-09-13 via `dev-01-define-padroes`. Aguardando primeira spec via `dev-02-escreve-spec`.

## Pendências

- [ ] Primeira spec via dev-02-escreve-spec
- [ ] Primeiro plano via dev-03-escreve-plano
- [ ] Setup de testes (framework + pasta + primeiro teste exemplar)

## Referências

- [[AMBIENTE.md]] — convenções globais da plataforma
- [[USUARIO.md]] — perfil do Orlando
- [[81-referencia/arquitetura.md]] — mapa estrutural do repo (mapa fino, isento — carga sob demanda)
- [[81-referencia/explicacoes/visao-geral.md]] — o quê e por quê (quadrante explicação, carga sob demanda)
- [[81-referencia/decisoes/]] — ADRs locais
