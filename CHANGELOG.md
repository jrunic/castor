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

## 0.4.0 — 16/09/2026

Medido nas máquinas do Walter (macOS 26.6.2, castor 0.3.0) e corrigido:

- **`curl | sh` acha o irmão.** No pipe, `$0` é `sh` e nada existe ao lado;
  o irmão agora é baixado da **mesma origem do pyz** (release, com
  `.sha256` publicado junto). O instalador do Python continua achando
  `instalar-python.sh` ao lado quando a execução é do checkout.
- **Python fora do PATH não-interativo é achado** — `CASTOR_BINS_EXTRA`
  aponta pastas extras (Homebrew: `/opt/homebrew/bin`), com caminho
  contendo espaço.
- **Tailscale no macOS:** a URL `tailscale-latest.pkg` media 404 — a
  instalar usa a versionada `Tailscale-1.102.4-macos.pkg` com soma
  conferida antes do `installer`; binário do app é resolvido ao caminho
  real (invocado por symlink, o CLI crashava).
- **`preparar` grava a cliente antes da pendência de expiração.** Código 6
  não apaga mais o cadastro; a saída nomeia a pendência e a reexecução a
  fecha.
- **Node 22 LTS opcional:** pergunta no `configurar` (default `n`) e flag
  `--node` no `preparar`. Mesmo padrão do Python: XDG 0700, tarball com
  soma (`SHASUMS256.txt` do nodejs.org), versão cavada
  (`22.23.2`), irmão `instalar-node.sh` anexo da release.

## 0.3.0 — 15/09/2026

**Mudança de superfície, sem alias:** o arquivo-mestre se chama **cadastro**
(`--cadastro`, `CASTOR_CADASTRO`, default `~/.config/castor/cadastro.json`,
lendo `castor.json` antigo), e o ensaio é **`--ensaio`** (antes `--seco`).

- **`castor configurar`** prepara a principal: chave (criar ou adotar, com
  prova por `ssh-keygen`), SMTP (Google ou outro, cofre 600), Tailscale
  (instala se faltar, login por URL; grava só com a rede `Running`).
- **Sem Python ≥3.12, o instalador baixa o 3.14** (*python-build-standalone*)
  para o XDG data e crava esse interpretador no wrapper.
- **`maquina preparar` instala Python 3.14 no XDG da conta de serviço** se
  ela não tiver 3.12; o cadastro da cliente grava esse interpretador.
- EOF no Enter da expiração não aborta mais o cadastro da cliente.

## 0.2.1 — 13/09/2026

- **O instalador acha o Python com nome versionado.** Ele procurava só
  `python3`, e no macOS esse é o 3.9 do sistema — a instalação era recusada em
  máquinas que tinham 3.12 instalado, com a mensagem mandando instalar o que já
  estava lá. Agora procura `python3`, `python3.15`, `python3.14`, `python3.13`,
  `python3.12`, obedece `CASTOR_PYTHON` quando declarado, e **diz qual
  interpretador escolheu** — escolha silenciosa é o que produz "funcionou na
  minha máquina".

  Consequência prática: `castor atualizacao rodar` passa a atualizar a **máquina
  principal** também, que é a metade macOS que a área prometia e não entregava.
- **A falha de um alvo da atualização diz o que a máquina respondeu.** Antes
  saía só o sintoma ("não respondeu depois da atualização"), descartando o erro
  padrão onde a causa está escrita.

## 0.2.0 — 13/09/2026

A máquina cliente passa a ser operada de ponta a ponta a partir da principal:
segredo entregue, serviço de pé, saúde vigiada e tudo em dia.

**Mudança de comportamento:** o caminho padrão do manifesto passou de
`./castor.json`, relativo ao diretório de onde se chama, para
`~/.config/castor/castor.json`. O cron da máquina cliente não tem diretório de
trabalho que alguém controle. `CASTOR_MANIFESTO` continua mandando.

- **A área `atualizacao`**: `rodar` e `estado`. Quatro tipos de alvo —
  `castor`, `pipx`, `npm` e `comando` — declarados no manifesto e atualizados a
  partir da principal. Cada um confere **que o comando ainda responde** depois:
  o gerenciador de pacotes sair zero não prova que o programa roda. Versão igual
  é "sem mudança", que não é falha. Código de saída **11**.
- **O castor é o último alvo, e o da principal por último de tudo** — um castor
  novo quebrado não derruba a rodada que já estava andando. A principal se
  atualiza **localmente**, sem ssh.
- **Alvo com `reiniciar`** chama o `servico reiniciar` quando a versão muda:
  atualizar o pacote e deixar o serviço rodando o binário velho é meio trabalho.
- **Esta versão não tem** idade mínima, confiança, aprovação nem rollback, e a
  referência diz isso em voz alta — material que cala sobre governança deixa
  quem lê supor que ela existe.

- **A área `ronda`**: `rodar` e `estado`. Você declara as checagens no
  manifesto — de comando, de serviço, ou de expiração de chave de nó — e a ronda
  **roda na máquina principal**, distribuindo as próprias perguntas. Não há
  limiar nem linha de base inventados pelo castor: quem declara o que conta como
  "bem" é quem opera. Código de saída **10** quando alguma checagem falha.
- **A checagem de expiração roda na principal**, que é o único lugar de onde ela
  é legível — uma máquina não lê a própria expiração de chave de nó. Efeito
  colateral útil: máquina fora do ar não impede essa checagem.
- **Máquina inalcançável é uma falha só**, não uma por checagem dela.
- **O aviso é por mudança de estado**: o que passou a falhar avisa uma vez por
  janela; o que voltou ao normal avisa também, e destrava o próximo aviso — sem
  isso, uma falha nova logo depois de um "voltou ao normal" ficaria muda até a
  janela vencer.
- **`ronda rodar --seco`** roda tudo sem avisar e sem gravar, para declarar
  checagem nova sem disparar e-mail.

- **A área `servico`**: `instalar`, `remover`, `estado`, `reiniciar` e
  `registro`. A unit systemd é gerada do manifesto — sem wrapper de shell, com
  `EnvironmentFile=` apontando para o que a área `segredos` entrega. `instalar`
  entrega o segredo antes de subir, e **confere que o serviço ficou ativo**;
  `remover` tira unit e segredo e confere que parou e desabilitou. Código de
  saída **9** quando o mundo não mudou. Linux apenas.
- **`instalar` liga o linger do usuário na cliente**, com sudo, e confere. Sem
  ele o serviço morreria quando a última sessão fechasse. **Isto muda a máquina
  além do castor:** o usuário passa a ter processos de pé sem sessão aberta. O
  `remover` não desliga o linger, porque ele pode estar sustentando outro
  serviço.
- **`servico reiniciar` é o que leva um segredo trocado ao processo** que o
  consome. Sem ele, entregar arquivo novo não mudava nada em memória.

- **A área `segredos` passa a trabalhar com um cofre.** Um arquivo de
  `CHAVE=valor` na máquina principal, que você edita; o manifesto diz quais
  chaves cada serviço recebe. `gerar <servico>` filtra e resolve. Sai o modelo
  com marca própria.
- **Duas marcas, `$HOME` e `$HOME_PRINCIPAL`**, resolvidas na geração a partir
  do que o cadastro mediu. Qualquer outro cifrão continua recusado.
- **`segredos enviar`** entrega o arquivo do serviço à cliente pela entrada
  padrão do ssh — sem arquivo temporário do outro lado — e leva junto o
  **manifesto-da-cliente**, que é só o que diz respeito àquela máquina. O cofre
  nunca vai.
- **`segredos estado`** diz, por serviço e máquina, se o que está lá corresponde
  ao que o cofre produziria hoje. Código de saída **8** quando algo está ausente
  ou desatualizado. Não imprime valor nenhum.
- **`maquina preparar` entrega a credencial de aviso** ao terminar, e a máquina
  já nasce sabendo avisar. Quando o serviço de aviso não está declarado, ele diz
  em voz alta que a máquina não sabe avisar, e o que fazer.
- **Correio fora do ar não derruba mais a rotina.** Uma rotina que falhava
  enquanto o servidor de e-mail estava inalcançável terminava com rastreamento
  em vez do próprio código de saída — e o diagnóstico ia parar no castor em vez
  de ir para o job.

## 0.1.1 — 13/09/2026

- **O instalador confere a soma publicada** do que baixou, antes de instalar.
  Sem a soma no lugar, ele **não instala** — quem quiser instalar assim mesmo
  passa `CASTOR_SEM_SOMA=1`. A soma pega arquivo truncado e artefato trocado sem
  que a soma fosse trocada junto; ela **não** cobre origem comprometida, porque
  arquivo e soma vêm do mesmo lugar.
- **`maquina preparar` instala o tailscale na cliente.** Na 0.1.0 ele só tentava
  subir a rede numa máquina onde o tailscale podia não existir — e o passo não
  conferia nada, então a falha passava em silêncio e só aparecia depois, como
  "o nó não aparece na rede". Agora instala, espera no máximo 20 segundos pelo
  endereço de login, e confere.
- **Re-rodar o `preparar` não duplica a chave** no `authorized_keys`.

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
