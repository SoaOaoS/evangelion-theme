#!/bin/bash
# Install every Evangelion theme into ~/.config/omarchy/themes/.
#
#   ./install.sh                 install the four themes
#   ./install.sh --extras        also install the fastfetch and starship configs
#   ./install.sh --set NAME      then switch to NAME (default: evangelion)
#
# Unlike `omarchy theme install <url>`, a copied theme is treated as your own,
# so Omarchy keeps its hyprland.lua (A.T. Field glow) and neovim.lua
# (bundled colorscheme) instead of regenerating them.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEMES_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/themes"
EXTRAS=0
SET_THEME=""

while (($#)); do
  case "$1" in
    --extras) EXTRAS=1 ;;
    --set) SET_THEME="${2:-evangelion}"; shift ;;
    -h | --help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# Files that make up a theme directory (everything else in the repo is tooling).
THEME_FILES=(
  colors.toml btop.theme icons.theme keyboard.rgb hyprland.lua neovim.lua
  unlock.png preview.png preview-unlock.png fastfetch.png light.mode
  shell.bar.toml shell.menu.toml shell.launcher.toml shell.notifications.toml
  shell.popups.toml shell.lock.toml
)

install_theme() {
  local from="$1" name="$2" dest="$THEMES_DIR/$2"

  if [[ -d $dest/.git ]]; then
    echo "  $name was installed with git; replacing it with a plain copy"
  fi
  rm -rf "$dest"
  mkdir -p "$dest"

  for f in "${THEME_FILES[@]}"; do
    [[ -e $from/$f ]] && cp "$from/$f" "$dest/"
  done
  cp -r "$from/backgrounds" "$dest/"
  echo "  ✓ $name"
}

echo "NERV // installing Evangelion themes into $THEMES_DIR"
mkdir -p "$THEMES_DIR"
install_theme "$SRC" evangelion
for variant in "$SRC"/variants/*/; do
  install_theme "${variant%/}" "$(basename "$variant")"
done

if ((EXTRAS)); then
  echo "NERV // installing extras"
  config="${XDG_CONFIG_HOME:-$HOME/.config}"
  mkdir -p "$config/fastfetch"
  for f in "$config/fastfetch/config.jsonc" "$config/starship.toml"; do
    [[ -f $f && ! -f $f.pre-evangelion ]] && cp "$f" "$f.pre-evangelion" && echo "  backup: $f.pre-evangelion"
  done
  cp "$SRC/extras/fastfetch/evangelion.template.jsonc" "$config/fastfetch/"
  cp "$SRC/extras/starship/starship.toml" "$config/starship.toml"
  mkdir -p "$HOME/.local/bin"
  cp "$SRC/extras/starship/evangelion-now-playing" "$HOME/.local/bin/"
  chmod +x "$HOME/.local/bin/evangelion-now-playing"
  command -v playerctl >/dev/null ||
    echo "  ! install playerctl for the now-playing segment: sudo pacman -S playerctl"

  # The portrait follows every theme switch through Omarchy's theme-set hook.
  hooks="$config/omarchy/hooks/theme-set.d"
  mkdir -p "$hooks"
  cp "$SRC/extras/fastfetch/evangelion-fastfetch" "$hooks/evangelion-fastfetch"
  chmod +x "$hooks/evangelion-fastfetch"
  bash "$hooks/evangelion-fastfetch" "${SET_THEME:-}"
  echo "  ✓ fastfetch + starship HUD"
fi

if [[ -n $SET_THEME ]]; then
  if command -v omarchy >/dev/null; then
    omarchy theme set "$SET_THEME"
  else
    omarchy-theme-set "$SET_THEME"
  fi
fi

echo "God's in his heaven. All's right with the world."
