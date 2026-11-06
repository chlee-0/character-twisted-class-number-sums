#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE=${APM_DOCKER_IMAGE:-character-twisted-class-number-sums:py3.13.5}
RUNTIME_DIR=${APM_RUNTIME_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/character-twisted-class-number-sums}

usage() {
  cat <<'EOF'
Usage:
  ./reproduce.sh build
  ./reproduce.sh verify-input
  ./reproduce.sh selected-prime-bundles
  ./reproduce.sh pairwise
  ./reproduce.sh survivors
  ./reproduce.sh all-local
  ./reproduce.sh verify-data [comma-separated figure groups]
  ./reproduce.sh verify-reference [comma-separated artifact groups]
  ./reproduce.sh export [destination] [comma-separated artifact groups]
  ./reproduce.sh shell

Generated data are written outside the checkout. Override their location with
APM_RUNTIME_DIR=/path/to/runtime. Override worker counts with APM_PROCESSES.
EOF
}

docker_run() {
  mkdir -p "$RUNTIME_DIR"
  docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --env APM_PROCESSES="${APM_PROCESSES:-4}" \
    --volume "$RUNTIME_DIR:/work/output" \
    "$@"
}

command=${1:-}
case "$command" in
  build)
    docker build --tag "$IMAGE" "$ROOT_DIR"
    ;;
  verify-input|selected-prime-bundles|pairwise|survivors|all-local)
    docker_run "$IMAGE" python scripts/run_profile.py "$command"
    ;;
  verify-data)
    verify_args=()
    if [[ $# -eq 2 ]]; then
      verify_args+=(--groups "$2")
    elif [[ $# -gt 2 ]]; then
      usage >&2
      exit 2
    fi
    docker_run "$IMAGE" python scripts/verify_figure_data.py "${verify_args[@]}"
    ;;
  verify-reference)
    verify_args=(--reference-hashes)
    if [[ $# -eq 2 ]]; then
      verify_args+=(--groups "$2")
    elif [[ $# -gt 2 ]]; then
      usage >&2
      exit 2
    fi
    docker_run "$IMAGE" python scripts/verify_artifacts.py "${verify_args[@]}"
    ;;
  export)
    if [[ $# -gt 3 ]]; then
      usage >&2
      exit 2
    fi
    target=${2:-"$ROOT_DIR/results"}
    mkdir -p "$target"
    target=$(realpath "$target")
    export_args=(--destination /export)
    if [[ $# -eq 3 ]]; then
      export_args+=(--groups "$3")
    fi
    docker_run --volume "$target:/export" "$IMAGE" \
      python scripts/export_artifacts.py "${export_args[@]}"
    ;;
  shell)
    docker_run --interactive --tty "$IMAGE" bash
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
