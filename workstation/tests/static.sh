#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
readonly PROJECT_ROOT
cd "$PROJECT_ROOT"

mapfile -t shell_files < <(
  find workstation/lib workstation/tests -type f -name '*.sh' -print
  printf '%s\n' \
    workstation-setup.sh \
    workstation/bin/workstation-setup \
    workstation/assets/cachy-workstation-microsip \
    packaging/build-workstation-installer.sh
)

for shell_file in "${shell_files[@]}"; do
  [[ $(head -n 1 "$shell_file") == '#!/usr/bin/env bash' ]] || {
    printf 'Missing Bash shebang: %s\n' "$shell_file" >&2
    exit 1
  }
  bash -n "$shell_file"
done
shellcheck -x "${shell_files[@]}"

desktop-file-validate workstation/assets/desktop/*.desktop
systemd-analyze verify workstation/systemd/cachy-workstation-idle.service

ruff check workstation/idle/idle-supervisor.py workstation/tests/test_idle_supervisor.py
ruff format --check workstation/idle/idle-supervisor.py workstation/tests/test_idle_supervisor.py
python -m unittest discover -s workstation/tests -p 'test_*.py' -v

build_dir=$(mktemp -d)
cleanup() {
  rm -rf --one-file-system "$build_dir"
}
trap cleanup EXIT

(
  exec 3>/dev/null
  # shellcheck source=workstation/lib/common.sh
  source "$PROJECT_ROOT/workstation/lib/common.sh"
  TARGET_HOME=$build_dir/path-safety-home
  TARGET_UID=$(id -u)
  TARGET_GID=$(id -g)
  mkdir -p "$TARGET_HOME/safe" "$build_dir/path-safety-outside"
  validate_target_managed_path "$TARGET_HOME/safe/new-directory" "safe path"
  ln -s "$build_dir/path-safety-outside" "$TARGET_HOME/linked"
  if validate_target_managed_path \
    "$TARGET_HOME/linked/new-directory" "linked path" >/dev/null 2>&1; then
    printf 'Symlinked managed path was accepted.\n' >&2
    exit 1
  fi
  if validate_target_managed_path \
    "$TARGET_HOME/../path-safety-outside" "traversal path" >/dev/null 2>&1; then
    printf 'Traversal managed path was accepted.\n' >&2
    exit 1
  fi
)

cmake \
  -S workstation/idle \
  -B "$build_dir" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON
cmake --build "$build_dir" --parallel "$(nproc)"

for package_name in google-chrome anydesk-bin zoiper-bin gtk2; do
  recipe_root=workstation/vendor/aur/$package_name
  diff -u "$recipe_root/.SRCINFO" <(
    cd "$recipe_root"
    makepkg --printsrcinfo
  )
  grep -Eq "^${package_name}[[:space:]]+[0-9a-f]{40}$" \
    workstation/vendor/aur/AUR-REVISIONS.txt
done

[[ -L workstation/vendor/aur/gtk2/LICENSES/0BSD.txt ]]
[[ $(readlink workstation/vendor/aur/gtk2/LICENSES/0BSD.txt) == ../LICENSE ]]

printf 'CachyWorkstation static tests: PASS\n'
