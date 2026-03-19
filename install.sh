#!/usr/bin/env bash
# install.sh — Install ccsetup into ~/.local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/bin"
TARGET="${TARGET_DIR}/ccsetup"
SHARE_DIR="${HOME}/.local/share/ccsetup"

echo ""
echo "  Installing ccsetup…"

mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/ccsetup.py" "$TARGET"
chmod +x "$TARGET"

echo "  ✔ Installed to: $TARGET"

# Install bundled MCP servers
mkdir -p "$SHARE_DIR"
for server in claude-mind claude-charter claude-witness claude-afe claude-retina claude-ledger; do
  if [[ -d "$SCRIPT_DIR/$server" ]]; then
    rm -rf "$SHARE_DIR/$server"
    cp -r "$SCRIPT_DIR/$server" "$SHARE_DIR/$server"
    echo "  ✔ $server → $SHARE_DIR/$server"
  fi
done

echo ""
echo "  Verifying bundled servers…"
for server in claude-mind claude-charter claude-witness claude-afe claude-retina claude-ledger; do
  srv="$SHARE_DIR/$server/server.py"
  if [[ -f "$srv" ]]; then
    echo "  ✔ $server"
  else
    echo "  ✘ $server — MISSING (check $SCRIPT_DIR/$server/)"
  fi
done

# ── PATH check (no-duplicate append) ─────────────────────────────────────────
if [[ ":${PATH}:" == *":${TARGET_DIR}:"* ]]; then
  echo "  ✔ ${TARGET_DIR} already in PATH"
else
  echo ""
  echo "  ⚠  ${TARGET_DIR} is not in PATH."

  # Detect shell profile
  if   [[ -f "${HOME}/.zshrc" ]];        then PROFILE="${HOME}/.zshrc"
  elif [[ -f "${HOME}/.bashrc" ]];       then PROFILE="${HOME}/.bashrc"
  elif [[ -f "${HOME}/.bash_profile" ]]; then PROFILE="${HOME}/.bash_profile"
  else PROFILE=""
  fi

  if [[ -n "$PROFILE" ]]; then
    # Only append if the PATH line is not already present (prevents duplicates)
    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
    if grep -qF "$PATH_LINE" "$PROFILE" 2>/dev/null; then
      echo "  ✔ PATH line already in ${PROFILE} (not duplicating)"
    else
      read -rp "  Add to ${PROFILE} now? [Y/n] " yn
      yn="${yn:-Y}"
      if [[ "$yn" =~ ^[Yy] ]]; then
        printf '\n# ccsetup (Claude Code bootstrapper)\n%s\n' "$PATH_LINE" >> "$PROFILE"
        echo "  ✔ Added to ${PROFILE}"
        echo "  → Restart terminal or: source ${PROFILE}"
      else
        echo "  → Add manually: ${PATH_LINE}"
      fi
    fi
  else
    echo "  → Add to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
fi

echo ""
echo "  Usage:"
echo "    ccsetup .                       # setup if needed, then launch Claude Code"
echo "    ccsetup . --continue            # launch with --continue (pass-through to claude)"
echo "    ccsetup . --setup               # force re-run setup even if already configured"
echo "    ccsetup . --status              # health-aware status report"
echo "    ccsetup . --dry-run             # preview without writing"
echo "    ccsetup . --preset recommended  # non-interactive curated setup"
echo "    ccsetup . --from-layer 3        # resume from a specific layer"
echo ""
