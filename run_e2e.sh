#!/usr/bin/env bash
"${BASH_SOURCE[0]}" >/dev/null 2>&1 || true
# Unified E2E runner for SalesTalk.
# Supports switching between Czech (default) and English test suites.
#
# Usage:
#   ./run_e2e.sh                # default: Czech suite (real AI)
#   ./run_e2e.sh --lang en      # English suite
#   ./run_e2e.sh --lang all     # Both Czech then English
#   ./run_e2e.sh --model llama3.2 --provider ollama --lang cs
#   ./run_e2e.sh --mock         # Use mock AI (fast)
#   ./run_e2e.sh --fast         # Smoke run (subset of Czech tests)
#   ./run_e2e.sh --limit 5      # Limit Czech param cases to N
#
# Flags:
#   --lang cs|en|all    Language selection (default: cs)
#   --model <name>      Ollama model (default: llama3.2)
#   --provider <p>      AI provider (ollama|bedrock) default: ollama
#   --mock              Force mock (disables real AI)
#   --help              Show help
#   --fast              Shortcut for --limit 5 (Czech only)
#   --limit N           For Czech suite, run only first N cases

set -euo pipefail

LANG_SEL="cs"
MODEL="llama3.2"
PROVIDER="ollama"
USE_MOCK="false"
LIMIT=""

while [[ $# -gt 0 ]]; do
	case "$1" in
		--lang)
			LANG_SEL="$2"; shift 2 ;;
		--model)
			MODEL="$2"; shift 2 ;;
		--provider)
			PROVIDER="$2"; shift 2 ;;
		--mock)
			USE_MOCK="true"; shift ;;
		--fast)
			LIMIT="5"; shift ;;
		--limit)
			LIMIT="$2"; shift 2 ;;
		--help|-h)
			grep '^#' "$0" | sed 's/^# //' | sed '1,2d'; exit 0 ;;
		*)
			echo "Unknown arg: $1" >&2; exit 1 ;;
	esac
done

cd /Users/pavel/Documents/Development/SalesTalk-3/backend
if [ -d .venv ]; then
	# shellcheck disable=SC1091
	source .venv/bin/activate || true
fi

export AI_PROVIDER="$PROVIDER"
export OLLAMA_MODEL="$MODEL"
export ENABLE_LANG_DETECT=true
export VERBOSE_E2E=true
export SUPPRESS_INFO_LOGS=true

if [ "$USE_MOCK" = "true" ]; then
	unset USE_REAL_AI
	echo "[E2E] Using MOCK AI provider (fast runs)" >&2
else
	export USE_REAL_AI=true
	echo "[E2E] Using REAL AI provider=$PROVIDER model=$MODEL" >&2
fi

run_pytest() {
	local file="$1"; shift || true
	local extra_args=("$@")
	echo "[E2E] $(date '+%H:%M:%S') Running: $file ${extra_args[*]}" >&2
	# Use verbose to see per-test progress and -s to stream prints
	python -m pytest -vv -s -ra "$file" "${extra_args[@]}" || return $?
}

# Build a subset of Czech nodeids if LIMIT is set
cz_subset_args() {
	if [[ -n "$LIMIT" ]]; then
		local n; n="${LIMIT}"
		local args=()
		for ((i=0; i< n; i++)); do
			args+=("tests/e2e/test_czech_questions.py::TestCzechQuestionSuite::test_question_row[${i}]")
		done
		printf '%s\n' "${args[@]}"
		return 0
	fi
	return 1
}

EXIT_CODE=0

case "$LANG_SEL" in
	cs)
		if subset_nodes=$(cz_subset_args); then
			run_pytest tests/e2e/test_czech_questions.py ${subset_nodes} || EXIT_CODE=$?
		else
			run_pytest tests/e2e/test_czech_questions.py || EXIT_CODE=$?
		fi ;;
	en)
		run_pytest tests/e2e/test_localstack_e2e.py || EXIT_CODE=$? ;;
	all)
		if subset_nodes=$(cz_subset_args); then
			run_pytest tests/e2e/test_czech_questions.py ${subset_nodes} || EXIT_CODE=$?
		else
			run_pytest tests/e2e/test_czech_questions.py || EXIT_CODE=$?
		fi
		run_pytest tests/e2e/test_localstack_e2e.py || EXIT_CODE=$? ;;
	*)
		echo "Unsupported --lang value: $LANG_SEL (use cs|en|all)" >&2
		exit 2 ;;
esac

if [ $EXIT_CODE -eq 0 ]; then
	echo "[E2E] Completed successfully for lang=$LANG_SEL" >&2
else
	echo "[E2E] Completed with failures (code $EXIT_CODE) for lang=$LANG_SEL" >&2
fi

exit $EXIT_CODE
