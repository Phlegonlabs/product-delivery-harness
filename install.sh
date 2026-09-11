#!/usr/bin/env bash
# Install the five Product Delivery Harness skills into a user skills directory.
# Any pre-existing copies are moved to one timestamped backup first — nothing is
# overwritten or deleted. Re-running this script is the update path.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skills_src="$repo_root/skills"
skills_dest="${1:-$HOME/.agents/skills}"
backup_root="${SKILL_BACKUP_ROOT:-$HOME/.agents/skill-backups/product-delivery-harness}"
skills=(
  delivery-harness
  product-definition-builder
  design-system-compiler
  code-security-review
  product-activation
)

for skill in "${skills[@]}"; do
  if [ ! -d "$skills_src/$skill" ]; then
    echo "error: missing skill directory $skills_src/$skill" >&2
    exit 1
  fi
done

mkdir -p "$skills_dest"

existing=()
for skill in "${skills[@]}"; do
  [ -d "$skills_dest/$skill" ] && existing+=("$skill")
done

if [ "${#existing[@]}" -gt 0 ]; then
  backup_dir="$backup_root/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$backup_dir"
  for skill in "${existing[@]}"; do
    mv "$skills_dest/$skill" "$backup_dir/$skill"
    echo "backed up existing $skill -> $backup_dir/$skill"
  done
fi

for skill in "${skills[@]}"; do
  target="$skills_dest/$skill"
  mkdir -p "$target"
  tar -C "$skills_src/$skill" --exclude='__pycache__' --exclude='*.pyc' -cf - . | tar -C "$target" -xf -
  if ! cmp -s "$skills_src/$skill/SKILL.md" "$target/SKILL.md"; then
    echo "error: $target/SKILL.md does not match the checkout" >&2
    exit 1
  fi
  echo "installed $skill -> $target"
done

echo "done. start a fresh host session so it discovers the skills."
