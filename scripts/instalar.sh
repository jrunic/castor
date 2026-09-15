#!/bin/sh
# Instalador de bootstrap do castor — o único shell do produto, porque a máquina
# ainda não tem o castor para se instalar sozinha. Variáveis de ambiente:
# CASTOR_DESTINO, CASTOR_ARTEFATO, CASTOR_URL, CASTOR_SEM_SOMA (veja o README).
set -eu

REPO="jrunic/castor"
DESTINO="${CASTOR_DESTINO:-$HOME/.local/bin}"
ARTEFATO="${CASTOR_ARTEFATO:-}"
MINIMO_MAIOR=3
MINIMO_MENOR=12

falhar() {
    printf '%s\n' "$1" >&2
    exit 1
}

somar() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        falhar "não achei sha256sum nem shasum para conferir o que baixei."
    fi
}

# Serve? Devolve a versão pela saída padrão, ou nada.
serve() {
    command -v "$1" >/dev/null 2>&1 || return 1
    v="$("$1" -V 2>&1 | awk '{print $2}')"
    maior="${v%%.*}"
    resto="${v#*.}"
    menor="${resto%%.*}"
    case "$maior$menor" in *[!0-9]*|"") return 1 ;; esac
    [ "$maior" -gt "$MINIMO_MAIOR" ] ||
        { [ "$maior" -eq "$MINIMO_MAIOR" ] && [ "$menor" -ge "$MINIMO_MENOR" ]; } ||
        return 1
    printf '%s' "$v"
}

# Medir por padrão, obedecer quando a ordem vier. O python3 do PATH pode ser o
# do sistema — no macOS ele é 3.9 mesmo havendo um 3.12 com nome versionado, e
# recusar ali seria mandar instalar o que já está instalado.
INTERPRETE=""
if [ -n "${CASTOR_PYTHON:-}" ]; then
    VERSAO="$(serve "$CASTOR_PYTHON")" ||
        falhar "CASTOR_PYTHON aponta para ${CASTOR_PYTHON}, que não serve: o castor precisa de ${MINIMO_MAIOR}.${MINIMO_MENOR} ou mais novo."
    INTERPRETE="$CASTOR_PYTHON"
else
    for candidato in python3 python3.15 python3.14 python3.13 python3.12; do
        VERSAO="$(serve "$candidato")" || continue
        INTERPRETE="$(command -v "$candidato")"
        break
    done
fi
if [ -z "$INTERPRETE" ]; then
    IRMAO="$(dirname "$0")/instalar-python.sh"
    INTERPRETE="$(sh "$IRMAO")" || falhar "não achei Python ${MINIMO_MAIOR}.${MINIMO_MENOR} e o instalador auxiliar falhou."
    VERSAO="$("$INTERPRETE" -V 2>&1 | awk '{print $2}')"
fi

# Escolha silenciosa é o que produz "funcionou na minha máquina".
printf 'usando %s (%s)\n' "$INTERPRETE" "$VERSAO"

TEMPORARIO="$(mktemp -d)"
limpar() { rm -r -f "$TEMPORARIO"; }
trap limpar EXIT

if [ -n "$ARTEFATO" ]; then
    cp "$ARTEFATO" "$TEMPORARIO/castor.pyz" ||
        falhar "não achei o artefato em ${ARTEFATO}."
else
    command -v curl >/dev/null 2>&1 || falhar "não achei curl para baixar o castor."
    URL="${CASTOR_URL:-https://github.com/${REPO}/releases/latest/download/castor.pyz}"
    curl -fsSL --connect-timeout 15 --max-time 300 "$URL" \
        -o "$TEMPORARIO/castor.pyz" && BAIXOU=0 || BAIXOU=$?
    if [ "$BAIXOU" -ne 0 ]; then
        # 22 é o servidor dizendo que não tem; o resto é a rede não chegar lá.
        if [ "$BAIXOU" -eq 22 ]; then
            falhar "o servidor respondeu que ${URL} não existe. Confira se já há release publicada."
        fi
        falhar "não consegui baixar ${URL}. A máquina tem saída para a internet?"
    fi

    # A soma publicada pega arquivo truncado e artefato trocado sem que a soma
    # fosse trocada junto. NÃO cobre origem comprometida: soma e arquivo vêm do
    # mesmo lugar, e quem puder trocar um troca o outro.
    if [ -z "${CASTOR_SEM_SOMA:-}" ]; then
        curl -fsSL --connect-timeout 15 "${URL}.sha256" \
            -o "$TEMPORARIO/soma" && TEVE=0 || TEVE=$?
        [ "$TEVE" -eq 0 ] ||
            falhar "não achei a soma publicada em ${URL}.sha256, então não instalo. Para instalar assim mesmo: CASTOR_SEM_SOMA=1."
        ESPERADA="$(awk '{print $1}' "$TEMPORARIO/soma")"
        OBTIDA="$(somar "$TEMPORARIO/castor.pyz")"
        [ "$ESPERADA" = "$OBTIDA" ] ||
            falhar "o arquivo baixado não bate com a soma publicada. Esperava ${ESPERADA}, veio ${OBTIDA}. Nada foi instalado."
    fi
fi

# Confere antes de instalar: o que não responde como castor não vira castor.
"$INTERPRETE" "$TEMPORARIO/castor.pyz" --versao >/dev/null 2>&1 ||
    falhar "o arquivo obtido não respondeu como castor. Nada foi instalado."

mkdir -p "$DESTINO"
cp "$TEMPORARIO/castor.pyz" "$DESTINO/castor.pyz"
# Fixa o interpretador conferido: 'python3' do PATH instalaria com um e rodaria
# com outro — no macOS, com o 3.9 do sistema.
cat > "$DESTINO/castor" <<ENVOLTORIO
#!/bin/sh
exec "$INTERPRETE" "\$(dirname "\$0")/castor.pyz" "\$@"
ENVOLTORIO
chmod 755 "$DESTINO/castor"

# E confere depois: exit 0 afirma sobre o processo, não sobre o mundo.
"$DESTINO/castor" --versao >/dev/null 2>&1 ||
    falhar "instalei em ${DESTINO}/castor mas o comando não respondeu."

printf 'castor instalado em %s\n' "$DESTINO/castor"
case ":$PATH:" in
    *":$DESTINO:"*) ;;
    *) printf 'acrescente %s ao seu PATH.\n' "$DESTINO" ;;
esac
