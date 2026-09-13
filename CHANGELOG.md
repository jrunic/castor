---
id: 202609132200
projeto: castor
tipo: nota
escopo: repo:castor
plataforma: "*"
status: ativo
descricao: Histórico de versões do castor.
tags: [changelog]
---

# Histórico de versões

## 0.1.0 — 13/09/2026

Primeira versão publicada.

### Existe

- **`chave`** — `criar`, `usar`, `mostrar`. A privada fica no lugar padrão do
  sistema; o manifesto guarda só o caminho. Nenhum verbo sobrescreve chave
  existente.
- **`maquina`** — `preparar`, `adicionar`, `listar`, `testar`, `remover`.
  `preparar` leva uma máquina recém-instalada a cliente: chave, usuário de
  serviço, sudo, castor instalado e rede privada. `adicionar` mede a máquina em
  vez de perguntar. `testar` separa rede inalcançável, chave recusada e castor
  ausente.
- **`rotina`** — `rodar`, `agendar`, `listar`. Trava, teto de tempo, registro e
  aviso por e-mail na falha, com supressão de repetição por janela.
- **`segredos`** — `gerar`, `ver`. **Em modelo antigo**, a mudar numa versão
  próxima.
- **Instalador de bootstrap** — confere a versão do Python antes, confere que o
  comando responde depois, e fixa no comando instalado o interpretador que
  passou na conferência.

### Não existe ainda

`servico`, `ronda` e `atualizacao` aparecem na ajuda e não têm verbos. Backup e
diagnóstico estão fora desta versão.

### O que a máquina cliente ainda não sabe fazer

Avisar por e-mail quando algo falha. A credencial de SMTP é um segredo, e a
entrega de segredos à cliente chega na próxima versão.

### Limitação conhecida

Uma máquina não consegue ler a própria expiração de chave de nó do tailscale —
o `tailscale status --json` não traz esse campo para o próprio nó. Por isso a
conferência roda na máquina principal, olhando a cliente.
