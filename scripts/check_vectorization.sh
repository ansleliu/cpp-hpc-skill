#!/usr/bin/env bash
set -uo pipefail

usage() {
  cat <<'EOF'
Usage: check_vectorization.sh [--compiler auto|gcc|clang|clang-cl|intel|msvc] [--output-dir DIR] [--] [COMPILER COMMAND...]

Run a GCC/Clang/Intel compiler command with vectorization-report flags and save
compiler output. If no command is supplied, print recommended flags only.
With auto and no command, print flags for every supported compiler family.

Examples:
  check_vectorization.sh -- g++ -O3 -c kernel.cpp -o kernel.o
  check_vectorization.sh --compiler clang -- clang++ -O3 -c kernel.cpp
  check_vectorization.sh --compiler msvc -- cl /O2 /c kernel.cpp
EOF
}

compiler="auto"
out_dir="vectorization-report-$(date +%Y%m%d-%H%M%S)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compiler)
      compiler="${2:?missing value after --compiler}"
      shift 2
      ;;
    --output-dir|-o)
      out_dir="${2:?missing value after --output-dir}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

kind="$compiler"
if [[ "$kind" == "auto" && $# -gt 0 ]]; then
  base="${1//\\//}"
  base="${base##*/}"
  base="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"
  base="${base%.exe}"
  case "$base" in
    clang-cl|clang-cl-*) kind="clang-cl" ;;
    clang|clang++|clang-*|clang++-*|*-clang|*-clang++|*-clang-[0-9]*|*-clang++-[0-9]*) kind="clang" ;;
    icc|icpc|icx|icpx|icc-[0-9]*|icpc-[0-9]*|icx-[0-9]*|icpx-[0-9]*) kind="intel" ;;
    cl) kind="msvc" ;;
    gcc|g++|c++|cc|gcc-[0-9]*|g++-[0-9]*|*-gcc|*-g++|*-gcc-[0-9]*|*-g++-[0-9]*) kind="gcc" ;;
    *) echo "Cannot identify compiler '$base'; select --compiler explicitly." >&2; exit 2 ;;
  esac
fi

select_flags() {
case "$1" in
  gcc)
    flags=(-fopt-info-vec-optimized -fopt-info-vec-missed)
    ;;
  clang)
    flags=(-Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize)
    ;;
  clang-cl)
    flags=(/clang:-Rpass=loop-vectorize /clang:-Rpass-missed=loop-vectorize /clang:-Rpass-analysis=loop-vectorize)
    ;;
  intel)
    flags=(-qopt-report=5 -qopt-report-phase=vec)
    ;;
  msvc)
    flags=(/Qvec-report:2)
    ;;
  *)
    echo "Unknown compiler kind: $1" >&2
    usage >&2
    return 2
    ;;
esac
}

if [[ "$kind" == "auto" && $# -eq 0 ]]; then
  for family in gcc clang clang-cl intel msvc; do
    select_flags "$family"
    echo "Recommended $family vectorization flags:"
    printf '  %s\n' "${flags[@]}"
  done
  exit 0
fi

select_flags "$kind" || exit $?

if [[ $# -eq 0 ]]; then
  echo "Recommended $kind vectorization flags:"
  printf '  %s\n' "${flags[@]}"
  exit 0
fi

mkdir -p "$out_dir" || exit 74
printf -v recorded_command '%q ' "$@" "${flags[@]}"
if ! printf '%s\n' "$recorded_command" > "$out_dir/command.txt" || ! : > "$out_dir/compiler-output.txt"; then
  echo "Cannot create vectorization report artifacts." >&2
  exit 74
fi

echo "Running compiler command with $kind vectorization-report flags."
echo "Output directory: $out_dir"
"$@" "${flags[@]}" > "$out_dir/compiler-output.txt" 2>&1
status=$?

{
  echo "compiler_kind=$kind"
  echo "exit_status=$status"
  echo "command=$recorded_command"
  echo "output=$out_dir/compiler-output.txt"
  if [[ $status -ne 0 ]]; then
    echo "note=compiler command failed; inspect output before interpreting vectorization diagnostics."
  fi
} | tee "$out_dir/summary.txt"
report_status=$?
if [[ $report_status -ne 0 ]]; then
  echo "Cannot save vectorization summary." >&2
  [[ $status -ne 0 ]] || status=74
fi

exit "$status"
