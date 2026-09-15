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

Duas partes: instalar o castor no **computador-principal**, depois preparar o
primeiro **computador-auxiliar**.

Os nomes deste guia são inventados.

Você vai precisar de uma conta no **Tailscale**. Criar a conta é grátis; o
castor instala o programa quando faltar.

## 1. Instalar o castor no computador-principal

```sh
curl -fsSL https://raw.githubusercontent.com/jrunic/castor/main/scripts/instalar.sh | sh
```

Instala em `~/.local/bin/castor`. Se não houver Python 3.12 ou mais novo, o
instalador põe o 3.14 em `~/.local/share/castor/python` e crava esse
interpretador no comando.

## 2. Configurar a principal

```sh
castor configurar
```

O comando pergunta se cria a chave ou se usa uma que você aponta, o nome desta
máquina, se você quer aviso por e-mail (Google ou outro) e instala o Tailscale
se ele não estiver no PATH. Só grava o cadastro e o cofre **depois** da rede
estar de pé. Não cole JSON à mão nesta etapa.

## 3. Conferir

```sh
castor maquina listar
```

## 4. Preparar a máquina cliente

```sh
castor maquina preparar computador-auxiliar \
  --endereco 192.168.1.50 \
  --usuario-inicial ubuntu
```

O comando vai, em ordem:

1. **Instalar sua chave para o usuário inicial.** É o único momento em que a
   senha é pedida — ela aparece no seu terminal, digitada por você.
2. **Medir a máquina:** usuário, diretório, sistema, relógio e fuso. A versão
   do Python do usuário inicial **não** recusa o preparo.
3. **Criar o usuário de serviço** (`castor`, por padrão), instalar a chave para
   ele e configurar o sudo. Uma senha pedida, uma vez.
4. **Provar a chave nova** numa conexão separada, antes de depender dela.
5. **Python na conta de serviço.** Se ela não tiver 3.12 ou mais novo, instala
   o 3.14 no XDG dela. Só então instala o castor, cravando esse interpretador.
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
castor maquina testar computador-auxiliar
```

`testar` responde de três jeitos diferentes quando dá errado, porque as
providências são diferentes: máquina fora do ar, chave recusada, ou castor
ausente do outro lado.

## 6. Pôr um serviço para rodar

O castor grava a unit do systemd e entrega o segredo do serviço. **O programa em
si você instala** — o castor não o baixa nem o compila.

Instale-o na cliente (do jeito que ele se instala: `pipx`, `npm`, um binário
copiado), e então declare o serviço no cadastro, com o `comando` apontando para
o caminho **absoluto** onde ele ficou:

```json
"sentinela": {
  "chaves": ["TOKEN_DA_SENTINELA"],
  "destino": "$HOME/.config/castor/sentinela.env",
  "comando": "/home/castor/.local/bin/sentinela --vigiar",
  "descricao": "Sentinela do computador-auxiliar",
  "maquinas": ["computador-auxiliar"]
}
```

Acrescente `TOKEN_DA_SENTINELA` ao cofre, e então:

```sh
castor servico instalar sentinela --maquina computador-auxiliar
castor servico estado
```

`instalar` entrega o segredo, grava a unit, liga o *linger* — que é o que faz o
serviço continuar de pé depois que você desconecta — e **confere que ficou
ativo**. Se não ficou, ele diz e manda você olhar o registro:

```sh
castor servico registro sentinela --maquina computador-auxiliar
```

Detalhes em [`servico.md`](../referencias/servico.md).

## 7. Ser avisado sem ter que lembrar

Duas coisas diferentes, e você provavelmente quer as duas.

**A rotina roda sozinha na cliente.** É o único caminho que não depende de
alguém dar comando. Declare no cadastro:

```json
"rotinas": {
  "checa-espaco": {
    "quando": "0 * * * *",
    "comando": "/usr/bin/test $(df -P / | awk 'NR==2 {print $5+0}') -lt 90",
    "maquina": "computador-auxiliar"
  }
}
```

Entregue e agende — o agendamento é feito **uma vez**, de dentro da cliente:

```sh
castor segredos enviar correio --maquina computador-auxiliar   # leva o cadastro dela junto
ssh castor@<endereço>
castor rotina agendar checa-espaco --maquina computador-auxiliar
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
    "sentinela-de-pe": {"tipo": "servico", "maquina": "computador-auxiliar",
                        "servico": "sentinela"},
    "computador-auxiliar-nao-expira": {"tipo": "expiracao", "maquina": "computador-auxiliar"}
  }
}
```

```sh
castor ronda rodar --ensaio     # vê o que daria, sem avisar ninguém
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
castor atualizacao rodar --ensaio   # o que faria
castor atualizacao rodar          # faz, e confere que o comando ainda responde
```

Detalhes em [`atualizacao.md`](../referencias/atualizacao.md).

## Depois: trocar um segredo

Editou o cofre? Entregue de novo, e confira:

```sh
castor segredos enviar correio --maquina computador-auxiliar
castor segredos estado
```

`estado` responde, por serviço e máquina, se o que está lá corresponde ao que o
cofre produziria hoje — sem imprimir valor nenhum.

**Se um serviço consome esse segredo, ele ainda está com o valor antigo em
memória.** Trocar o arquivo não mexe no processo:

```sh
castor servico reiniciar sentinela --maquina computador-auxiliar
```

## Quando der errado

| O que aparece | O que fazer |
|---|---|
| `não respondeu` | a máquina está ligada e na rede? o endereço está certo? |
| `recusou a chave` | rode `castor chave mostrar` e confira se ela está no `authorized_keys` daquele usuário |
| `a identidade de ... mudou` | a máquina foi reinstalada — ou alguém está no meio do caminho. Confirme antes de apagar a linha de `~/.ssh/known_hosts` |
| `o castor não está instalado` | rode `castor maquina preparar` |
| `o python desta máquina é 3.9` | o passo na conta de serviço falhou; o `preparar` tenta o 3.14 sozinho — se repetir, a máquina não baixa o tarball |
| `a expiração de ... continua ativa` | desative no painel do Tailscale e rode de novo — a conferência não mente |
| `o serviço ... ficou 'failed'` | `castor servico registro <nome> --maquina <máquina>` diz o que ele falou ao morrer |
| `o cofre ... não tem <CHAVE>` | acrescente a linha no cofre da principal e rode de novo |
| `... pode ser lido por outros usuários` | `chmod 600` no cofre |
| `não há chave declarada no cadastro` | `castor chave criar` |
