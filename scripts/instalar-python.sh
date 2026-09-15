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
TAR="${CASTOR_PYTHON_ARTEFATO:-}"
TMP="$(mktemp -d)"
trap 'rm -r -f "$TMP"' EXIT
if [ -z "$TAR" ]; then
    command -v curl >/dev/null 2>&1 || falhar "não achei curl para baixar o Python."
    case "$(uname -s)" in Darwin) OS=apple-darwin ;; Linux) OS=unknown-linux-gnu ;; *) falhar "SO não suportado para instalar Python." ;; esac
    case "$(uname -m)" in arm64|aarch64) CPU=aarch64 ;; x86_64) CPU=x86_64 ;; *) falhar "CPU não suportada." ;; esac
    falhar "aponta o tarball 3.14 com CASTOR_PYTHON_ARTEFATO (cpython ${CPU}-${OS})."
fi
[ -f "$TAR" ] || falhar "não achei o artefato em ${TAR}."
if [ -z "${CASTOR_PYTHON_SEM_SOMA:-}" ]; then
    [ -f "${TAR}.sha256" ] || falhar "não achei ${TAR}.sha256; CASTOR_PYTHON_SEM_SOMA=1 para pular."
    ESPERADA="$(awk '{print $1}' "${TAR}.sha256")"
    OBTIDA="$(somar "$TAR")"
    [ "$ESPERADA" = "$OBTIDA" ] || falhar "soma do tarball não bate. Nada foi extraído."
fi
mkdir -p "$DEST"
chmod 700 "$DEST"
tar -xzf "$TAR" -C "$DEST"
PY="$(find "$DEST" -type f -name python3 | head -n 1)"
[ -n "$PY" ] || falhar "o tarball não trouxe python3."
chmod 755 "$PY"
printf '%s\n' "$PY"
