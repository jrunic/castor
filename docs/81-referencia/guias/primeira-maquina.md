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

**Antes de começar**, a máquina nova precisa de três coisas, e só três: estar
ligada na rede, ter o servidor de SSH ativo, e ter um usuário criado na
instalação do sistema (com senha). É o que qualquer instalador de Linux
entrega. O resto sai daqui, da máquina principal.

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

## 3. Preparar a máquina cliente

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
6. **Ligar a máquina à rede privada** e imprimir um endereço para você abrir no
   navegador desta máquina, onde você já está autenticado. Um clique.
7. **Conduzir a desativação da expiração da chave de nó** — mostra o caminho no
   painel, espera, e confere. Se a expiração continuar ativa, o comando **não**
   anuncia sucesso: quando a data chegar, a máquina sai da rede e o acesso vai
   embora junto.

Se algum passo rodar sem produzir efeito, o comando para ali e diz qual foi. A
máquina continua acessível pelo caminho anterior — nenhum passo que fecha um
acesso roda antes de o acesso novo ter sido provado.

## 4. Conferir

```sh
castor maquina listar
castor maquina testar represa
```

`testar` responde de três jeitos diferentes quando dá errado, porque as
providências são diferentes: máquina fora do ar, chave recusada, ou castor
ausente do outro lado.

## O que ainda falta

A máquina está de pé, mas **ainda não sabe avisar quando algo falha**. A
credencial de e-mail é um segredo, e segredo chega pela entrega do cofre — que
é a área `segredos`. Enquanto isso não for feito, uma rotina pode falhar em
silêncio.

## Quando der errado

| O que aparece | O que fazer |
|---|---|
| `não respondeu` | a máquina está ligada e na rede? o endereço está certo? |
| `recusou a chave` | rode `castor chave mostrar` e confira se ela está no `authorized_keys` daquele usuário |
| `a identidade de ... mudou` | a máquina foi reinstalada — ou alguém está no meio do caminho. Confirme antes de apagar a linha de `~/.ssh/known_hosts` |
| `o castor não está instalado` | rode `castor maquina preparar` |
| `o python desta máquina é 3.9` | instale um Python 3.12 ou mais novo e repita |
| `a expiração de ... continua ativa` | desative no painel e rode de novo — a conferência é local e não mente |
