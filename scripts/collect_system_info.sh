#!/usr/bin/env bash
set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
  exec python3 "$script_dir/collect_system_info.py" "$@"
fi
if command -v python >/dev/null 2>&1 && python -c 'import sys' >/dev/null 2>&1; then
  exec python "$script_dir/collect_system_info.py" "$@"
fi

usage() {
  cat <<'EOF'
Usage: collect_system_info.sh [--json FILE] [--text FILE]

Run the cross-platform Python collector. If Python is unavailable, write a
minimal Linux summary and an explicit JSON warning without fabricating data.
EOF
}

json_out="system-info.json"
text_out="system-info.txt"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      json_out="${2:?missing file after --json}"
      shift 2
      ;;
    --text)
      text_out="${2:?missing file after --text}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Python is unavailable and fallback does not support argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

json_string() {
  local value="$1" encoded="" character code i LC_ALL=C
  for ((i=0; i<${#value}; i++)); do
    character="${value:i:1}"
    printf -v code '%d' "'$character"
    if ((code == 34 || code == 92)); then
      encoded+="\\$character"
    elif ((code < 32)); then
      printf -v character '\\u%04x' "$code"
      encoded+="$character"
    else
      encoded+="$character"
    fi
  done
  printf '"%s"' "$encoded"
}

mkdir -p "$(dirname "$json_out")" "$(dirname "$text_out")" || exit 74
{
  echo "# Minimal system information summary"
  echo
  date -u '+Created: %Y-%m-%dT%H:%M:%SZ'
  echo
  echo "## uname"
  uname -a 2>&1 || echo "unavailable"
  echo
  echo "## lscpu"
  lscpu 2>&1 || echo "unavailable"
  echo
  echo "## memory"
  free -h 2>&1 || echo "unavailable"
} | cat > "$text_out" || { echo "Cannot save fallback text." >&2; exit 74; }

{
  printf '{"schema_version":1,"warning":"Python unavailable; see minimal text summary","text_file":' &&
  json_string "$text_out" && printf '}\n'
} > "$json_out" || { echo "Cannot save fallback JSON." >&2; exit 74; }
echo "Wrote fallback JSON: $json_out"
echo "Wrote fallback text: $text_out"
