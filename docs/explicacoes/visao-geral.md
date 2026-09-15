---
id: 202609131101
projeto: castor
tipo: explicacao
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: O quê/para quem em 30 segundos — visão geral do repo castor (quadrante explicação, ADR 20260713).
tags: [explicacao, visao-geral, Python]
---

# castor — o quê / para quem

O castor cuida da infraestrutura de uma máquina pessoal: guarda segredos e os
entrega aos serviços, mantém serviço de pé, roda rotina periódica avisando
quando falha, e mantém a máquina atualizada.

## Para quem

Quem opera a própria máquina sem uma equipe de infraestrutura atrás — e o
agente de IA que opera junto. A superfície é descobrível por `castor --help`,
de propósito: um agente precisa conseguir descobrir o que a ferramenta faz sem
que alguém lhe conte.

## O que faz

- **segredos** — um segredo declarado uma vez, entregue a cada serviço só no
  que lhe cabe.
- **servico** — instalar, remover e acompanhar serviço de sistema sem escrever
  arquivo de unit à mão.
- **rotina** — agendar e executar tarefa periódica com trava, teto de tempo,
  registro e aviso por e-mail quando falha.
- **ronda** — checagens de saúde declaradas pelo próprio usuário, não herdadas
  de outra máquina.
- **atualizacao** — manter atualizados os alvos declarados, e o próprio castor
  junto.

## Escopo

**Dentro:** uma pessoa, poucas máquinas, o que cabe num cadastro declarado à
mão.

**Fora:** frota, motor de incidentes com escalação, política de confiança e
aprovação de versão. Quem precisa disso precisa de outra classe de ferramenta.

## Princípio

Nada da máquina de quem usa é cravado no código. Nome de máquina, usuário,
diretório e caminho vivem no cadastro — código com host embutido é defeito,
não configuração.
