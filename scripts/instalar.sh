#!/bin/sh
# Instalador de bootstrap do castor. É o único shell do produto: existe porque
# a máquina ainda não tem o castor para se instalar sozinha.
#
# Variáveis de ambiente:
#   CASTOR_DESTINO   onde instalar (padrão: ~/.local/bin)
#   CASTOR_ARTEFATO  caminho de um castor.pyz local, no lugar do download
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
    URL="https://github.com/${REPO}/releases/latest/download/castor.pyz"
    curl -fsSL "$URL" -o "$TEMPORARIO/castor.pyz" ||
        falhar "não consegui baixar ${URL}. A máquina tem saída para a internet?"
fi

# Confere antes de instalar: o que não responde como castor não vira castor.
"$INTERPRETE" "$TEMPORARIO/castor.pyz" --versao >/dev/null 2>&1 ||
    falhar "o arquivo obtido não respondeu como castor. Nada foi instalado."

mkdir -p "$DESTINO"
cp "$TEMPORARIO/castor.pyz" "$DESTINO/castor.pyz"
# O envoltório fixa o interpretador conferido acima. Chamar 'python3' do PATH
# instalaria com um python e rodaria com outro — no macOS, com o 3.9 do sistema.
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
