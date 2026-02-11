#!/usr/bin/env bash
set -euo pipefail

# Resolve the repo root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "Error: skills/ directory not found at $SKILLS_SRC" >&2
  exit 1
fi

# Discover available skills
mapfile -t SKILLS < <(find "$SKILLS_SRC" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | grep -v '^_' | sort)

if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "Error: no skills found in $SKILLS_SRC" >&2
  exit 1
fi

# --- Destination prompt ---
echo "Install skills to:"
echo "  1) Global   (~/.claude/skills/)"
echo "  2) Project  (.claude/skills/ in current directory)"
echo ""
read -rp "Choose [1/2]: " dest_choice

case "$dest_choice" in
  1) DEST="$HOME/.claude/skills" ;;
  2) DEST="$(pwd)/.claude/skills" ;;
  *)
    echo "Invalid choice." >&2
    exit 1
    ;;
esac

# --- Skill selection ---
echo ""
echo "Available skills:"
for i in "${!SKILLS[@]}"; do
  echo "  $((i + 1))) ${SKILLS[$i]}"
done
echo "  a) All"
echo ""
read -rp "Choose skill(s) (comma-separated numbers, or 'a' for all): " skill_choice

selected=()
if [[ "$skill_choice" == "a" || "$skill_choice" == "A" ]]; then
  selected=("${SKILLS[@]}")
else
  IFS=',' read -ra picks <<< "$skill_choice"
  for pick in "${picks[@]}"; do
    pick="$(echo "$pick" | tr -d ' ')"
    if [[ ! "$pick" =~ ^[0-9]+$ ]] || (( pick < 1 || pick > ${#SKILLS[@]} )); then
      echo "Invalid selection: $pick" >&2
      exit 1
    fi
    selected+=("${SKILLS[$((pick - 1))]}")
  done
fi

if [[ ${#selected[@]} -eq 0 ]]; then
  echo "No skills selected." >&2
  exit 1
fi

# --- Copy skills ---
for skill in "${selected[@]}"; do
  target="$DEST/$skill"

  if [[ -d "$target" ]]; then
    overwrite=""
    read -rp "Skill '$skill' already exists at $target. Overwrite? [y/N]: " overwrite || true
    if [[ "$overwrite" != "y" && "$overwrite" != "Y" ]]; then
      echo "  Skipping $skill"
      continue
    fi
    rm -rf "$target"
  fi

  mkdir -p "$target"
  cp -r "$SKILLS_SRC/$skill"/. "$target"
  echo "  Installed $skill -> $target"
done

echo ""
echo "Done."
