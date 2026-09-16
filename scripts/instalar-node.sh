#!/bin/sh
# Irmão do instalar.sh para Node 22 LTS — mesmo padrão do Python: XDG data,
# 0700, tarball com soma. Teto: 80 linhas.
set -eu
if [ -n "${XDG_DATA_HOME:-}" ] && [ "${XDG_DATA_HOME#/}" != "$XDG_DATA_HOME" ]; then
    DEST="$XDG_DATA_HOME/castor/node"
else
    DEST="$HOME/.local/share/castor/node"
fi
falhar() { printf '%s\n' "$1" >&2; exit 1; }
somar() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
    else falhar "não achei sha256sum nem shasum."; fi
}
# A versão é contrato commitado, não descoberta por API em runtime.
NODE_VERSION="22.23.2"
TMP="$(mktemp -d)"
trap 'rm -r -f "$TMP"' EXIT
TAR="${CASTOR_NODE_ARTEFATO:-}"
if [ -z "$TAR" ]; then
    command -v curl >/dev/null 2>&1 || falhar "não achei curl para baixar o Node."
    case "$(uname -s)" in Darwin) OS=darwin ;; Linux) OS=linux ;; *) falhar "SO não suportado." ;; esac
    case "$(uname -m)" in arm64|aarch64) CPU=arm64 ;; x86_64) CPU=x64 ;; *) falhar "CPU não suportada." ;; esac
    URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-${OS}-${CPU}.tar.gz"
    TAR="$TMP/node.tgz"
    curl -fsSL --connect-timeout 15 --max-time 300 "$URL" -o "$TAR" ||
        falhar "não baixei o Node ${NODE_VERSION} de ${URL}."
    curl -fsSL --connect-timeout 15 "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" \
        -o "$TMP/SHASUMS256.txt" || falhar "não baixei os SHASUMS256 do Node."
    ESPERADA="$(grep "node-v${NODE_VERSION}-${OS}-${CPU}.tar.gz\$" "$TMP/SHASUMS256.txt" | awk '{print $1}')"
    [ -n "$ESPERADA" ] || falhar "o SHASUMS256 não traz o tarball desta máquina."
else
    [ -f "$TAR" ] || falhar "não achei o artefato em ${TAR}."
    ESPERADA="${CASTOR_NODE_SOMA_ESPERADA:-}"
    if [ -z "$ESPERADA" ] && [ -f "${TAR}.sha256" ]; then
        ESPERADA="$(awk '{print $1}' "${TAR}.sha256")"
    fi
fi
if [ -n "$ESPERADA" ]; then
    OBTIDA="$(somar "$TAR")"
    [ "$ESPERADA" = "$OBTIDA" ] || falhar "a soma do tarball do Node não bate. Nada foi extraído."
else
    falhar "sem soma para conferir: passe CASTOR_NODE_SOMA_ESPERADA ou ${TAR}.sha256."
fi
mkdir -p "$DEST"
chmod 700 "$DEST"
tar -xzf "$TAR" -C "$DEST"
NODE="$(find "$DEST" \( -type f -o -type l \) -name node | sed -n '1p')"
[ -n "$NODE" ] || falhar "o tarball não trouxe bin/node."
chmod 755 "$NODE"
printf '%s\n' "$NODE"
