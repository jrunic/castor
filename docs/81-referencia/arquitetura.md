---
id: 202609131101
projeto: castor
tipo: arquitetura
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Mapa estrutural do repo castor — módulos, fluxos críticos, schema, deploy. Carga sob demanda.
tags: [arquitetura, Python]
---

# Arquitetura do Projeto: castor

> **Mapa fino (espinha de navegação, ADR 20260713).** Este arquivo diz *o que existe e onde* e
> **aponta** para `explicacoes/` — nunca duplica conteúdo de design. Se uma seção crescer em prosa
> de "por quê", mova para `docs/81-referencia/explicacoes/` e deixe só o ponteiro. O `dev-08 auditar`
> fiscaliza mapa gordo.

## Visão geral

CLI em Python de um comando só, `castor`, com áreas de subcomandos. Roda na
**máquina principal** e comanda **máquinas clientes** por SSH; nas clientes,
roda também localmente (rotina, ronda). Stdlib apenas, sem código nativo,
distribuída como arquivo único.

```
castor/
├── README.md         — entrypoint humano
├── CONTEXTO.md       — padrões técnicos + restrições (carga default; raiz)
├── 91-diario/        — diários de sessão
├── scripts/
│   ├── build-pyz.py  — empacota src/ em castor.pyz
│   └── instalar.sh   — instalador de bootstrap (o único shell do produto)
├── src/castor/       — o pacote
├── tests/            — pytest
└── docs/81-referencia/ — arquitetura.md (este), decisoes/, dominio/ + quadrantes Diátaxis
```

## Módulos principais

| Módulo | Responsabilidade |
|---|---|
| `cli.py` | Analisa a linha de comando, despacha por área, traduz erro em código de saída |
| `manifesto.py` | Lê, resolve e **escreve** o manifesto; papel principal/cliente; escrita atômica |
| `chaves.py` | Criar, adotar e mostrar a chave de acesso. Nunca sobrescreve |
| `conexao.py` | **Fronteira de sistema**: monta a invocação do `ssh` e nomeia o fracasso |
| `medicao.py` | A sonda e a interpretação do que a máquina respondeu sobre si |
| `rede.py` | Tailscale: subida, URL de login, expiração de chave de nó |
| `preparar.py` | Roteiro de passos com efeito conferido e prova exigida |
| `unidade.py` | O texto da unit systemd de um serviço, e o que ela recusa |
| `ronda.py` | As checagens declaradas, o que cada uma conclui, e a comparação com a ronda anterior |
| `cofre.py` | Ler o cofre, recusar permissão frouxa, filtrar por serviço, resolver as duas marcas |
| `segredos.py` | Montar o conteúdo de um serviço, somar, e descrever sem revelar |
| `cliente.py` | Montar o manifesto-da-cliente a partir do da principal |
| `rotina.py` | Envolve a execução: trava, teto de tempo, registro, alarme |
| `agenda.py` | Entradas do castor no agendador do sistema |
| `correio.py` | Monta e envia o aviso. Não decide se envia |
| `supressao.py` | Decide se este alarme já foi avisado na janela |

## Fluxos críticos

**Preparar uma máquina** (`cli._preparar_maquina` → `preparar.montar_roteiro` →
`preparar.executar`): o roteiro é uma lista de passos, cada um com `fazer`,
`conferir` e `exige`. `executar` roda em ordem, confere o efeito de cada um e
recusa passo cuja prova declarada ainda não aconteceu. É o que impede fechar um
caminho de acesso antes de o novo funcionar.

**Falar com a cliente** (`conexao`): três modos, e a diferença é de propósito —
em lote (saída capturada, autenticação por chave), com senha (terminal
repassado, só no primeiro acesso) e com terminal (para `sudo` que ainda pede
senha). Código 255 do ssh vira `RedeInalcancavel`, `ChaveRecusada` ou
`FalhaDeConexao`; qualquer outro código é resposta do comando remoto.

**Rodar uma rotina** (`cli._despachar_rotina` → `rotina.rodar`): trava, teto de
tempo, registro, e no caminho de falha o `correio`, filtrado pela `supressao`.

## Schema/persistência

Manifesto JSON na principal, em `~/.config/castor/castor.json` (formato em
`referencias/chave-e-maquina.md` e `referencias/segredos-e-cofre.md`); cofre de
`CHAVE=valor` ao lado dele; manifesto-da-cliente no mesmo caminho, em cada
cliente. Estado de execução em
`$CASTOR_ESTADO` (padrão `~/.local/state/castor`): registros, travas e o
arquivo de avisos já enviados.

## Deploy

Arquivo único `castor.pyz` (`scripts/build-pyz.py`), instalado por
`scripts/instalar.sh`, que confere a versão do Python e **fixa o interpretador
conferido** no comando instalado. Não publica em registro de pacote.

## Testes

pytest, em `tests/`. Runner canônico: `.venv/bin/pytest` na raiz — o `python3`
de sistema do macOS é 3.9 e não serve. Mock só na fronteira de SSH e de SMTP;
o resto roda com código real.

## Estado atual

Áreas `chave`, `maquina`, `segredos`, `servico`, `rotina` e `ronda` de pé, com o
instalador de bootstrap. `atualizacao` ainda sem verbos.
