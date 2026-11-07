#!/usr/bin/env bash
set -uo pipefail

usage() {
  cat <<'EOF'
Usage: perf_stat.sh [--repeat N] [--events LIST] [--extended] [--output-dir DIR] -- COMMAND [ARGS...]

Probe requested Linux perf events, run the supported subset, and preserve raw
CSV plus diagnostics. No system settings are changed. Unsupported events and
permission failures are reported instead of being hidden or fabricated.
EOF
}

repeat=5
events="task-clock,context-switches,cpu-migrations,page-faults,cycles,instructions,branches,branch-misses,cache-references,cache-misses"
extended_events="LLC-loads,LLC-load-misses,dTLB-loads,dTLB-load-misses"
out_dir="perf-stat-$(date +%Y%m%d-%H%M%S)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repeat|-r)
      repeat="${2:?missing value after --repeat}"
      shift 2
      ;;
    --events|-e)
      events="${2:?missing value after --events}"
      shift 2
      ;;
    --extended)
      events="$events,$extended_events"
      shift
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
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "Missing command. Use -- before the benchmark command." >&2
  usage >&2
  exit 2
fi

if ! command -v perf >/dev/null 2>&1; then
  echo "perf not found; no counters collected." >&2
  exit 127
fi

mkdir -p "$out_dir" || exit 74
printf -v recorded_command '%q ' "$@"
printf '%s\n' "$recorded_command" > "$out_dir/command.txt" || exit 74

IFS=',' read -r -a requested_events <<< "$events"
available_events=()
skipped_events=()
probe_log="$out_dir/event-probe.txt"
: > "$probe_log" || exit 74

for event in "${requested_events[@]}"; do
  event="${event//[[:space:]]/}"
  [[ -z "$event" ]] && continue
  probe_output="$out_dir/.probe.csv"
  probe_error="$out_dir/.probe.err"
  if perf stat -x, -e "$event" -o "$probe_output" -- true 2> "$probe_error"; then
    available_events+=("$event")
    echo "available: $event" >> "$probe_log" || exit 74
  else
    skipped_events+=("$event")
    echo "skipped: $event" >> "$probe_log" || exit 74
    sed 's/^/  /' "$probe_error" >> "$probe_log" || exit 74
  fi
done
rm -f "$out_dir/.probe.csv" "$out_dir/.probe.err" || exit 74

if [[ ${#available_events[@]} -eq 0 ]]; then
  echo "No requested perf events are available; see $probe_log" >&2
  exit 69
fi

available_csv="$(IFS=,; echo "${available_events[*]}")"
raw_csv="$out_dir/perf-stat.csv"
diagnostics="$out_dir/perf-diagnostics.txt"
summary="$out_dir/summary.txt"

exec 3> "$diagnostics" || exit 74
echo "Running perf stat. Output directory: $out_dir"
perf stat -x, -r "$repeat" -e "$available_csv" -o "$raw_csv" -- "$@" 2>&3 3>&-
status=$?
exec 3>&-

{
  echo "repeat=$repeat"
  echo "requested_events=$events"
  echo "available_events=$available_csv"
  echo "skipped_events=$(IFS=,; echo "${skipped_events[*]}")"
  echo "command=$recorded_command"
  echo "perf_exit_status=$status"
  echo "raw_csv=$raw_csv"
  echo "diagnostics=$diagnostics"
  echo "event_probe=$probe_log"
  if [[ $status -ne 0 ]]; then
    echo "note=perf failed during the benchmark; inspect diagnostics and do not infer missing counters."
  fi
} | tee "$summary"
report_status=$?
if [[ $report_status -ne 0 ]]; then
  echo "Cannot save perf summary." >&2
  [[ $status -ne 0 ]] || status=74
fi

exit "$status"
