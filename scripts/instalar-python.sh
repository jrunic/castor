#!/bin/sh
# Irmão do instalar.sh: põe CPython 3.14 no XDG data. Teto: 80 linhas.
set -eu
if [ -n "${XDG_DATA_HOME:-}" ] && [ "${XDG_DATA_HOME#/}" != "$XDG_DATA_HOME" ]; then
    DEST="$XDG_DATA_HOME/castor/python"
else
    DEST="$HOME/.local/share/castor/python"
fi
falhar() { printf '%s\n' "$1" >&2; exit 1; }
somar() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
    else falhar "não achei sha256sum nem shasum."; fi
}
TMP="$(mktemp -d)"
trap 'rm -r -f "$TMP"' EXIT
TAR="${CASTOR_PYTHON_ARTEFATO:-}"
if [ -z "$TAR" ]; then
    command -v curl >/dev/null 2>&1 || falhar "não achei curl para baixar o Python."
    case "$(uname -s)" in Darwin) OS=apple-darwin ;; Linux) OS=unknown-linux-gnu ;; *) falhar "SO não suportado." ;; esac
    case "$(uname -m)" in arm64|aarch64) CPU=aarch64 ;; x86_64) CPU=x86_64 ;; *) falhar "CPU não suportada." ;; esac
    URL="${CASTOR_PYTHON_URL:-}"
    if [ -z "$URL" ]; then
        URL="$(curl -fsSL --connect-timeout 15 https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest |
            tr '"' '\n' | grep "cpython-3.14" | grep "${CPU}-${OS}-install_only.tar.gz" |
            grep -v freethreaded | grep -v musl | sed -n '1p')"
        [ -n "$URL" ] || falhar "não achei tarball 3.14 para ${CPU}-${OS}."
    fi
    TAR="$TMP/cpython.tgz"
    curl -fsSL --connect-timeout 15 --max-time 300 "$URL" -o "$TAR" || falhar "não baixei o Python 3.14."
    curl -fsSL --connect-timeout 15 "${URL}.sha256" -o "$TAR.sha256" || rm -f "$TAR.sha256"
fi
[ -f "$TAR" ] || falhar "não achei o artefato em ${TAR}."
if [ -z "${CASTOR_PYTHON_SEM_SOMA:-}" ] && [ -f "${TAR}.sha256" ]; then
    ESPERADA="$(awk '{print $1}' "${TAR}.sha256")"
    OBTIDA="$(somar "$TAR")"
    [ "$ESPERADA" = "$OBTIDA" ] || falhar "soma do tarball não bate. Nada foi extraído."
elif [ -z "${CASTOR_PYTHON_SEM_SOMA:-}" ] && [ -n "${CASTOR_PYTHON_ARTEFATO:-}" ]; then
    falhar "não achei ${TAR}.sha256; CASTOR_PYTHON_SEM_SOMA=1 para pular."
fi
mkdir -p "$DEST"
chmod 700 "$DEST"
tar -xzf "$TAR" -C "$DEST"
PY="$(find "$DEST" -type f -name python3 | sed -n '1p')"
[ -n "$PY" ] || falhar "o tarball não trouxe python3."
chmod 755 "$PY"
printf '%s\n' "$PY"
