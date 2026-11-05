#!/usr/bin/env bash
# Enlaza la memoria de Claude Code de este proyecto a .claude/memory/ del repo,
# para que se versione con git. Correr una vez después de clonar.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Claude Code guarda la memoria por proyecto en ~/.claude/projects/<ruta-con-/-y-.-como-->/memory
SLUG="$(printf '%s' "$REPO" | sed 's|[/.]|-|g')"
TARGET="$HOME/.claude/projects/$SLUG/memory"

mkdir -p "$(dirname "$TARGET")"

if [ -L "$TARGET" ]; then
  echo "Ya existe el symlink: $TARGET -> $(readlink "$TARGET")"
  exit 0
fi

if [ -d "$TARGET" ]; then
  # Hay memoria local previa: se copia al repo sin pisar archivos existentes.
  cp -n "$TARGET"/*.md "$REPO/.claude/memory/" 2>/dev/null || true
  mv "$TARGET" "$TARGET.bak.$(date +%s)"
  echo "Memoria local previa respaldada en $TARGET.bak.*"
fi

ln -s "$REPO/.claude/memory" "$TARGET"
echo "OK: $TARGET -> $REPO/.claude/memory"
