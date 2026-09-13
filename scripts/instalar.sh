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

INTERPRETE="$(command -v python3 || true)"
[ -n "$INTERPRETE" ] ||
    falhar "não achei python3. O castor precisa de Python ${MINIMO_MAIOR}.${MINIMO_MENOR} ou mais novo."

VERSAO="$("$INTERPRETE" -V 2>&1 | awk '{print $2}')"
MAIOR="${VERSAO%%.*}"
RESTO="${VERSAO#*.}"
MENOR="${RESTO%%.*}"
if [ "$MAIOR" -lt "$MINIMO_MAIOR" ] ||
   { [ "$MAIOR" -eq "$MINIMO_MAIOR" ] && [ "$MENOR" -lt "$MINIMO_MENOR" ]; }; then
    falhar "o python desta máquina é ${VERSAO}; o castor precisa de ${MINIMO_MAIOR}.${MINIMO_MENOR} ou mais novo. Instale um mais novo e rode de novo."
fi

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
