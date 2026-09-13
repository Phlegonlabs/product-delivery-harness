#!/usr/bin/env bash
# Install the seven Product Delivery Harness skills into a user skills directory.
# The source is staged and verified before mutation. Existing managed copies are
# moved to one timestamped backup, and any failure restores that backup.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skills_src="$repo_root/skills"
skills_dest="${1:-$HOME/.agents/skills}"
backup_root="${SKILL_BACKUP_ROOT:-$HOME/.agents/skill-backups/product-delivery-harness}"
skills=(
  delivery-harness
  product-definition-builder
  ui-design-builder
  design-system-compiler
  code-security-review
  product-activation
  seo-growth-review
)
legacy_skills=(
  full-harness
  prd-builder
  product-design-builder
)
managed_skills=("${skills[@]}" "${legacy_skills[@]}")
required_commands=(
  cmp
  cp
  date
  diff
  find
  git
  mkdir
  mktemp
  mv
  rm
  rmdir
  sleep
  sort
)

stage_root=""
backup_dir=""
attempt_id="pdh-$(date +%Y%m%d-%H%M%S)-$$-$RANDOM"
lock_dir=""
lock_owned=0
installed=()
moved=()

fail() {
  echo "error: $*" >&2
  exit 1
}

for command_name in "${required_commands[@]}"; do
  command -v "$command_name" >/dev/null 2>&1 ||
    fail "required command is unavailable: $command_name"
done

for skill in "${skills[@]}"; do
  source_dir="$skills_src/$skill"
  [ -d "$source_dir" ] || fail "missing skill directory $source_dir"
  [ -f "$source_dir/SKILL.md" ] || fail "missing $source_dir/SKILL.md"
done

is_cache_file() {
  case "$1" in
    *__pycache__/*|.pytest_cache/*|*/.pytest_cache/*|*.pyc|*.pyo) return 0 ;;
    *) return 1 ;;
  esac
}

is_forbidden_source_file() {
  local value="/$1/"
  case "$value" in
    */.env.example/*|*/.env.*.example/*|*/.dev.vars.example/*) return 1 ;;
    */.env/*|*/.env.*/*|*/.dev.vars/*|*/.dev.vars.*/*|*/.DS_Store/*|*/Thumbs.db/*|*/thumbs.db/*|*/.idea/*|*/.vscode/*|*/node_modules/*|*.log/*) return 0 ;;
    *) return 1 ;;
  esac
}

write_source_manifest() {
  local skill="$1" output="$2" tracked relative
  : >"$output"
  while IFS= read -r tracked; do
    [ -n "$tracked" ] || continue
    relative="${tracked#"skills/$skill/"}"
    [ "$relative" != "$tracked" ] || fail "unexpected tracked path for $skill: $tracked"
    is_cache_file "$relative" && continue
    is_forbidden_source_file "$relative" && fail "forbidden tracked source artifact: skills/$skill/$relative"
    printf '%s\n' "$relative" >>"$output"
  done < <(git -C "$repo_root" ls-files -- "skills/$skill")
  LC_ALL=C sort -o "$output" "$output"
  [ -s "$output" ] || fail "$skill tracked manifest is empty"
}

check_untracked_source_files() {
  local skill="$1" path relative
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    relative="${path#"skills/$skill/"}"
    is_cache_file "$relative" && continue
    fail "untracked source artifact is not installable: $path"
  done < <(git -C "$repo_root" ls-files --others --exclude-standard -- "skills/$skill")
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    relative="${path#"skills/$skill/"}"
    is_cache_file "$relative" && continue
    fail "ignored source artifact is not installable: $path"
  done < <(git -C "$repo_root" ls-files --others --ignored --exclude-standard -- "skills/$skill")
}

write_manifest() {
  local root="$1" output="$2" file relative
  : >"$output"
  while IFS= read -r -d '' file; do
    relative="${file#"$root"/}"
    if is_cache_file "$relative" || [ "$relative" = ".pdh-install-owner" ]; then
      continue
    fi
    printf '%s\n' "$relative" >>"$output"
  done < <(find "$root" -type f -print0)
  LC_ALL=C sort -o "$output" "$output"
}

verify_tree() {
  local source="$1" target="$2" label="$3"
  local source_manifest="$stage_root/.manifests/${label}.source"
  local target_manifest="$stage_root/.manifests/${label}.target"
  local relative file_count=0

  write_source_manifest "$label" "$source_manifest"
  write_manifest "$target" "$target_manifest"
  if ! cmp -s "$source_manifest" "$target_manifest"; then
    echo "error: $label file manifest does not match $source" >&2
    diff -u "$source_manifest" "$target_manifest" >&2 || true
    return 1
  fi

  while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    if ! cmp -s "$source/$relative" "$target/$relative"; then
      echo "error: $label file does not byte-match: $relative" >&2
      return 1
    fi
    file_count=$((file_count + 1))
  done <"$source_manifest"

  [ "$file_count" -gt 0 ] || fail "$label manifest is empty"
}

copy_tracked_tree() {
  local skill="$1" target="$2" manifest="$stage_root/.manifests/${skill}.copy" relative target_file target_parent
  write_source_manifest "$skill" "$manifest"
  mkdir "$target"
  while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    target_file="$target/$relative"
    target_parent="${target_file%/*}"
    [ "$target_parent" = "$target_file" ] || mkdir -p "$target_parent"
    cp -p "$skills_src/$skill/$relative" "$target_file"
  done <"$manifest"
}

release_lock() {
  local owner owner_value=""
  [ "$lock_owned" -eq 1 ] && [ -n "$lock_dir" ] && [ -d "$lock_dir" ] || return 0
  owner="$lock_dir/owner"
  if [ -f "$owner" ]; then
    IFS= read -r owner_value <"$owner" || true
  fi
  if [ -f "$owner" ] && [ "$owner_value" != "$attempt_id" ]; then
    echo "error: refusing to remove an install lock not owned by this attempt: $lock_dir" >&2
    return 1
  fi
  if [ -f "$owner" ]; then
    rm -- "$owner"
  fi
  if [ ! -e "$owner" ]; then
    rmdir "$lock_dir"
    lock_dir=""
    lock_owned=0
    return 0
  fi
  return 1
}

restore_install() {
  local restore_status=0 skill target owner_value

  for skill in ${installed[@]+"${installed[@]}"}; do
    target="$skills_dest/$skill"
    owner_value=""
    if [ -f "$target/.pdh-install-owner" ]; then
      IFS= read -r owner_value <"$target/.pdh-install-owner" || true
    fi
    if { [ -f "$target/.pdh-install-owner" ] && [ "$owner_value" = "$attempt_id" ]; } ||
       { [ ! -e "$target/.pdh-install-owner" ] && [ "$lock_owned" -eq 1 ]; }; then
      rm -rf -- "$target" || restore_status=1
    elif [ -e "$target" ]; then
      echo "error: preserving partial target not owned by this attempt: $target" >&2
      restore_status=1
    fi
  done

  if [ -n "$backup_dir" ]; then
    for skill in ${moved[@]+"${moved[@]}"}; do
      target="$skills_dest/$skill"
      [ -e "$backup_dir/$skill" ] || continue
      if [ -e "$target" ]; then
        echo "error: cannot restore $skill because $target still exists" >&2
        restore_status=1
        continue
      fi
      mv "$backup_dir/$skill" "$target" || restore_status=1
    done
    if [ -d "$backup_dir" ] && ! rmdir "$backup_dir" 2>/dev/null; then
      restore_status=1
    fi
  fi

  if [ -n "$stage_root" ] && [ -d "$stage_root" ]; then
    rm -rf -- "$stage_root" || restore_status=1
  fi
  release_lock || restore_status=1
  return "$restore_status"
}

on_failure() {
  local status="${1:-$?}"
  trap - EXIT
  if ! restore_install; then
    echo "error: rollback finished with errors; the timestamped backup is preserved" >&2
    status=1
  fi
  exit "$status"
}
trap on_failure EXIT
trap 'on_failure 129' HUP
trap 'on_failure 130' INT
trap 'on_failure 143' TERM

for skill in "${skills[@]}"; do
  check_untracked_source_files "$skill"
done

mkdir -p "$skills_dest"
skills_dest_abs="$(cd "$skills_dest" && pwd -P)"
skills_src_abs="$(cd "$skills_src" && pwd -P)"
case "$skills_dest_abs" in
  "$skills_src_abs"|"$skills_src_abs"/*) fail "destination overlaps repository skills: $skills_dest_abs" ;;
esac
case "$skills_src_abs" in
  "$skills_dest_abs"/*) fail "destination contains repository skills: $skills_dest_abs" ;;
esac
lock_candidate="$skills_dest/.pdh-install.lock"
if ! mkdir "$lock_candidate" 2>/dev/null; then
  fail "another install owns destination lock: $lock_candidate"
fi
lock_dir="$lock_candidate"
lock_owned=1
if [ -n "${PDH_INSTALL_TEST_FAIL_LOCK_OWNER:-}" ]; then
  fail "induced lock owner marker failure"
fi
printf '%s\n' "$attempt_id" >"$lock_dir/owner"
if [ -n "${PDH_INSTALL_TEST_HOLD_LOCK_SECONDS:-}" ]; then
  sleep "$PDH_INSTALL_TEST_HOLD_LOCK_SECONDS"
fi
stage_root="$(mktemp -d "$skills_dest/.pdh-install-stage.XXXXXX")"
mkdir -p "$stage_root/.manifests"

for skill in "${skills[@]}"; do
  copy_tracked_tree "$skill" "$stage_root/$skill"
done

# Test-only corruption hook. It changes a staged non-SKILL file before the
# pre-install equality gate, so tests can prove every file is checked.
if [ -n "${PDH_INSTALL_TEST_CORRUPT_STAGE:-}" ]; then
  case "$PDH_INSTALL_TEST_CORRUPT_STAGE" in
    ../*|*/../*|/*) fail "invalid staged corruption path" ;;
  esac
  corrupt_file="$stage_root/$PDH_INSTALL_TEST_CORRUPT_STAGE"
  [ -f "$corrupt_file" ] || fail "corruption test path is not a staged file"
  printf '\nexpected test corruption\n' >>"$corrupt_file"
fi

for skill in "${skills[@]}"; do
  verify_tree "$skills_src/$skill" "$stage_root/$skill" "$skill"
done

mkdir -p "$backup_root"
backup_root_abs="$(cd "$backup_root" && pwd -P)"
case "$backup_root_abs" in
  "$skills_dest_abs"|"$skills_dest_abs"/*) fail "backup root must stay outside destination: $backup_root_abs" ;;
esac
existing=()
for skill in "${managed_skills[@]}"; do
  [ -e "$skills_dest/$skill" ] && existing+=("$skill")
done

if [ "${#existing[@]}" -gt 0 ]; then
  stamp="$(date +%Y%m%d-%H%M%S)"
  backup_dir="$backup_root/$stamp"
  collision=1
  while [ -e "$backup_dir" ]; do
    backup_dir="$backup_root/$stamp-$collision"
    collision=$((collision + 1))
  done
  mkdir "$backup_dir"
  for skill in "${existing[@]}"; do
    moved+=("$skill")
    mv "$skills_dest/$skill" "$backup_dir/$skill"
    echo "backed up existing $skill -> $backup_dir/$skill"
  done
fi

for skill in "${skills[@]}"; do
  target="$skills_dest/$skill"
  if [ "${PDH_INSTALL_TEST_CREATE_FOREIGN_TARGET:-}" = "$skill" ]; then
    mkdir "$target"
    printf 'foreign sentinel\n' >"$target/keep.txt"
  fi
  mkdir "$target"
  installed+=("$skill")
  if [ "${PDH_INSTALL_TEST_FAIL_OWNER_MARKER:-}" = "$skill" ]; then
    fail "induced target owner marker failure for $skill"
  fi
  printf '%s\n' "$attempt_id" >"$target/.pdh-install-owner"
  cp -a "$stage_root/$skill/." "$target/"
  echo "installed $skill -> $target"
  if [ "${PDH_INSTALL_FAIL_AFTER:-}" = "$skill" ]; then
    fail "induced failure after installing $skill"
  fi
done

for skill in "${skills[@]}"; do
  verify_tree "$skills_src/$skill" "$skills_dest/$skill" "$skill"
done
for skill in "${legacy_skills[@]}"; do
  [ ! -e "$skills_dest/$skill" ] || fail "legacy skill remains installed: $skill"
done

for skill in "${skills[@]}"; do
  owner="$skills_dest/$skill/.pdh-install-owner"
  owner_value=""
  if [ -f "$owner" ]; then
    IFS= read -r owner_value <"$owner" || true
  fi
  [ -f "$owner" ] && [ "$owner_value" = "$attempt_id" ] ||
    fail "installed target ownership marker changed: $skills_dest/$skill"
done

for skill in "${skills[@]}"; do
  owner="$skills_dest/$skill/.pdh-install-owner"
  rm -- "$owner"
done

rm -rf -- "$stage_root"
stage_root=""
release_lock
trap - EXIT HUP INT TERM

echo "done. start a fresh host session so it discovers the skills."
