---
id: 202609132100
projeto: castor
tipo: guia
escopo: repo:castor
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Como pôr a primeira máquina cliente de pé com o castor — da chave de acesso ao cadastro, com o que fica faltando depois
tags: [guia, chave, maquina, ssh, tailscale]
---

# Pôr a primeira máquina de pé

Leva uma máquina recém-instalada a máquina cliente: alcançável por chave,
medida, com o castor instalado e ligada à rede privada.

**Antes de começar**, a máquina nova precisa de:

1. estar ligada e na rede;
2. servidor de SSH ativo;
3. um usuário criado na instalação, **com sudo** — o castor cria um usuário de
   serviço, e para isso usa o sudo desse primeiro usuário;
4. **Python 3.12 ou mais novo instalado.** O castor confere e **não instala**:
   Debian 12 traz 3.11 e Ubuntu 22.04 traz 3.10, e nessas o preparo para no
   passo do Python, dizendo isso. Distribuições de 2024 em diante costumam
   trazer 3.12+.

Os três primeiros qualquer instalador de Linux entrega. O quarto é o que mais
surpreende, e é melhor conferir antes: `python3 -V` na máquina nova.

Você também vai precisar de uma conta no **Tailscale** — é a rede privada que o
castor usa para as máquinas se enxergarem de qualquer lugar. Criar a conta é
grátis e leva um minuto; o castor instala o programa na máquina nova sozinho.

O resto sai daqui, da máquina principal.

Os nomes deste guia são inventados: `bancada` é a máquina principal e `represa`
é a cliente.

## 1. A chave de acesso

```sh
castor chave criar
```

Gera o par em `~/.ssh/castor` e anota o caminho no manifesto. Se você já tem
uma chave que quer usar:

```sh
castor chave usar ~/.ssh/id_ed25519
```

Nenhum dos dois sobrescreve chave existente. Chave sobrescrita é acesso
perdido, e o castor não faz isso por conta própria.

## 2. Cadastrar a máquina principal

```sh
castor maquina adicionar bancada --principal
```

A principal é esta máquina, a que você usa. Ela guarda a chave, o manifesto e —
mais adiante — o cofre de segredos. As clientes executam; a cliente nunca
acessa a principal.

Repare que você não digitou diretório, usuário nem sistema: o comando mediu.
Campo digitado é caminho errado que ninguém vai saber diagnosticar depois.

## 3. O cofre, se você quer ser avisado

Se você quer que a máquina saiba avisar por e-mail quando algo falhar — e quer —
o cofre precisa existir antes. Ele é um arquivo que você edita:

```sh
mkdir -p ~/.config/castor
cat > ~/.config/castor/cofre <<'FIM'
SMTP_SERVIDOR=smtp.seuprovedor.test
SMTP_PORTA=587
SMTP_USUARIO=voce@seuprovedor.test
SMTP_SENHA=a-senha-de-aplicativo
FIM
chmod 600 ~/.config/castor/cofre
```

Agora o manifesto precisa saber onde o cofre está e quem recebe o quê. **Essa
parte você escreve à mão** — não há comando que escreva no manifesto, de
propósito: quem guarda segredo é você, e uma ferramenta que escreve no cofre é
uma ferramenta que pode apagá-lo.

Abra `~/.config/castor/castor.json` (o `castor maquina adicionar` já o criou) e
acrescente três blocos ao que já está lá:

```json
{
  "chave": "/Users/ana/.ssh/castor",
  "maquinas": {
    "bancada": { "papel": "principal", "usuario": "ana", "casa": "/Users/ana",
                 "sistema": "darwin", "endereco": "", "python": "3.12.14" }
  },

  "cofre": "/Users/ana/.config/castor/cofre",

  "servicos": {
    "correio": {
      "chaves": ["SMTP_SERVIDOR", "SMTP_PORTA", "SMTP_USUARIO", "SMTP_SENHA"],
      "destino": "$HOME/.config/castor/correio.env",
      "maquinas": ["represa"]
    }
  },

  "aviso": {
    "servico": "correio",
    "servidor": "smtp.seuprovedor.test", "porta": 587,
    "usuario": "voce@seuprovedor.test",
    "de": "voce@seuprovedor.test",
    "para": "voce@seuprovedor.test",
    "janela_em_minutos": 60,
    "arquivo_de_segredo": "$HOME/.config/castor/correio.env",
    "variavel": "SMTP_SENHA"
  }
}
```

Três coisas que confundem na primeira vez:

- **`represa` ainda não existe** — ela nasce no passo 4. Declarar aqui a máquina
  que vai receber é normal; a entrega só acontece depois que ela existe.
- **`$HOME` é o da máquina que vai usar o arquivo**, não o seu. Na cliente ele
  vira `/home/castor`. As duas marcas aceitas são `$HOME` e `$HOME_PRINCIPAL`, e
  qualquer outro cifrão é recusado.
- **`castor.json` é dois arquivos diferentes**: este, o seu, que fica na
  principal e tem tudo; e o da cliente, que o castor gera e entrega, com só o que
  diz respeito a ela. **O cofre nunca vai.**

O formato completo de cada bloco está nas referências de
[`segredos`](../referencias/segredos-e-cofre.md),
[`servico`](../referencias/servico.md), [`rotina`](../referencias/rotina.md) e
[`ronda`](../referencias/ronda.md).

Com isso no lugar, o `preparar` do passo seguinte termina entregando a
credencial à máquina, e ela já nasce sabendo avisar. Sem isso, ele diz em voz
alta que a máquina **não sabe avisar**, e o que fazer para consertar.

## 4. Preparar a máquina cliente

```sh
castor maquina preparar represa \
  --endereco 192.168.1.50 \
  --usuario-inicial ubuntu
```

O comando vai, em ordem:

1. **Instalar sua chave para o usuário inicial.** É o único momento em que a
   senha é pedida — ela aparece no seu terminal, digitada por você.
2. **Medir a máquina:** usuário, diretório, sistema, relógio, fuso e versão do
   Python.
3. **Criar o usuário de serviço** (`castor`, por padrão), instalar a chave para
   ele e configurar o sudo. Uma senha pedida, uma vez.
4. **Provar a chave nova** numa conexão separada, antes de depender dela.
5. **Instalar o castor** na cliente.
6. **Instalar o Tailscale e ligar a máquina à sua rede privada.** Ele imprime um
   endereço; abra no navegador **desta** máquina, onde você já está logado no
   Tailscale, e autorize. Um clique.
7. **Entregar a credencial de aviso**, se o cofre estiver declarado.
8. **Conduzir a desativação da expiração da chave de nó.** Por padrão o
   Tailscale faz cada máquina expirar a cada alguns meses — quando isso
   acontece, a máquina sai da rede e o seu acesso a ela vai junto. Desativar
   isso só se faz no painel do Tailscale; o castor mostra o caminho, espera, e
   **confere**. Se continuar ativa, ele não anuncia sucesso.

Se algum passo rodar sem produzir efeito, o comando para ali e diz qual foi. A
máquina continua acessível pelo caminho anterior — nenhum passo que fecha um
acesso roda antes de o acesso novo ter sido provado.

## 5. Conferir

```sh
castor maquina listar
castor maquina testar represa
```

`testar` responde de três jeitos diferentes quando dá errado, porque as
providências são diferentes: máquina fora do ar, chave recusada, ou castor
ausente do outro lado.

## 6. Pôr um serviço para rodar

O castor grava a unit do systemd e entrega o segredo do serviço. **O programa em
si você instala** — o castor não o baixa nem o compila.

Instale-o na cliente (do jeito que ele se instala: `pipx`, `npm`, um binário
copiado), e então declare o serviço no manifesto, com o `comando` apontando para
o caminho **absoluto** onde ele ficou:

```json
"sentinela": {
  "chaves": ["TOKEN_DA_SENTINELA"],
  "destino": "$HOME/.config/castor/sentinela.env",
  "comando": "/home/castor/.local/bin/sentinela --vigiar",
  "descricao": "Sentinela da represa",
  "maquinas": ["represa"]
}
```

Acrescente `TOKEN_DA_SENTINELA` ao cofre, e então:

```sh
castor servico instalar sentinela --maquina represa
castor servico estado
```

`instalar` entrega o segredo, grava a unit, liga o *linger* — que é o que faz o
serviço continuar de pé depois que você desconecta — e **confere que ficou
ativo**. Se não ficou, ele diz e manda você olhar o registro:

```sh
castor servico registro sentinela --maquina represa
```

Detalhes em [`servico.md`](../referencias/servico.md).

## 7. Ser avisado sem ter que lembrar

Duas coisas diferentes, e você provavelmente quer as duas.

**A rotina roda sozinha na cliente.** É o único caminho que não depende de
alguém dar comando. Declare no manifesto:

```json
"rotinas": {
  "checa-espaco": {
    "quando": "0 * * * *",
    "comando": "/usr/bin/test $(df -P / | awk 'NR==2 {print $5+0}') -lt 90",
    "maquina": "represa"
  }
}
```

Entregue e agende — o agendamento é feito **uma vez**, de dentro da cliente:

```sh
castor segredos enviar correio --maquina represa   # leva o manifesto dela junto
ssh castor@<endereço>
castor rotina agendar checa-espaco --maquina represa
castor rotina listar
```

A partir daí, se o comando falhar, chega um e-mail — um por janela, não um por
execução. Detalhes em [`rotina.md`](../referencias/rotina.md).

**A ronda você roda, da principal.** Ela olha várias coisas de uma vez, inclusive
as que a própria máquina não consegue responder sobre si:

```json
"ronda": {
  "janela_em_minutos": 360,
  "checagens": {
    "sentinela-de-pe": {"tipo": "servico", "maquina": "represa",
                        "servico": "sentinela"},
    "represa-nao-expira": {"tipo": "expiracao", "maquina": "represa"}
  }
}
```

```sh
castor ronda rodar --seco     # vê o que daria, sem avisar ninguém
castor ronda rodar            # a primeira de verdade
castor ronda estado           # o que deu na última, sem reexecutar
```

**A ronda não se agenda sozinha nesta versão** — ela é rodada por você, ou no
check-in combinado. É por isso que o `estado` diz há quanto tempo foi a última:
ronda velha dá sensação de vigilância sem a vigilância.

Detalhes em [`ronda.md`](../referencias/ronda.md).

## 8. Manter tudo em dia

```sh
castor atualizacao estado         # que versão está onde
castor atualizacao rodar --seco   # o que faria
castor atualizacao rodar          # faz, e confere que o comando ainda responde
```

Detalhes em [`atualizacao.md`](../referencias/atualizacao.md).

## Depois: trocar um segredo

Editou o cofre? Entregue de novo, e confira:

```sh
castor segredos enviar correio --maquina represa
castor segredos estado
```

`estado` responde, por serviço e máquina, se o que está lá corresponde ao que o
cofre produziria hoje — sem imprimir valor nenhum.

**Se um serviço consome esse segredo, ele ainda está com o valor antigo em
memória.** Trocar o arquivo não mexe no processo:

```sh
castor servico reiniciar sentinela --maquina represa
```

## Quando der errado

| O que aparece | O que fazer |
|---|---|
| `não respondeu` | a máquina está ligada e na rede? o endereço está certo? |
| `recusou a chave` | rode `castor chave mostrar` e confira se ela está no `authorized_keys` daquele usuário |
| `a identidade de ... mudou` | a máquina foi reinstalada — ou alguém está no meio do caminho. Confirme antes de apagar a linha de `~/.ssh/known_hosts` |
| `o castor não está instalado` | rode `castor maquina preparar` |
| `o python desta máquina é 3.9` | instale um Python 3.12 ou mais novo e repita |
| `a expiração de ... continua ativa` | desative no painel do Tailscale e rode de novo — a conferência não mente |
| `o serviço ... ficou 'failed'` | `castor servico registro <nome> --maquina <máquina>` diz o que ele falou ao morrer |
| `o cofre ... não tem <CHAVE>` | acrescente a linha no cofre da principal e rode de novo |
| `... pode ser lido por outros usuários` | `chmod 600` no cofre |
| `não há chave declarada no manifesto` | `castor chave criar` |
