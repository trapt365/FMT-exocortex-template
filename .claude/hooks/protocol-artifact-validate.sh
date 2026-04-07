#!/bin/bash
# Protocol Artifact Validation Hook
# Event: PreToolUse (matcher: Bash)
# Intercepts `git commit` in protocol-managed repos to validate artifacts.
# Returns block decision if artifact fails validation.
# Read-only: only returns JSON, does not modify files.
#
# Validated artifacts:
#   - DayPlan: 11 required sections (day-open protocol)
#   - DayClose: итоги, carry-over (day-close protocol) [future]
#
# Parameterized: sections list is a variable, not hardcoded per format.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only trigger on Bash tool with git commit command
if [ "$TOOL" != "Bash" ]; then
  echo '{}'
  exit 0
fi

# Check if command contains git commit (but not git commit --amend or other non-standard)
if ! echo "$TOOL_INPUT" | grep -qE 'git (add.*&&.*git )?commit'; then
  echo '{}'
  exit 0
fi

# Check if we're in DS-my-strategy (protocol governance repo)
if ! echo "$TOOL_INPUT" | grep -q 'DayPlan\|day-open\|day-close\|WeekPlan'; then
  # Also check pwd context — look for staged DayPlan files
  STAGED=$(cd ${IWE_GOVERNANCE_REPO:-~/IWE/DS-my-strategy} 2>/dev/null && git diff --cached --name-only 2>/dev/null || echo "")
  if ! echo "$STAGED" | grep -qE 'DayPlan|WeekPlan'; then
    echo '{}'
    exit 0
  fi
fi

# --- DayPlan Validation ---
DAYPLAN=$(ls ${IWE_GOVERNANCE_REPO:-~/IWE/DS-my-strategy}/current/DayPlan\ *.md 2>/dev/null | head -1)

if [ -z "$DAYPLAN" ]; then
  echo '{}'
  exit 0
fi

# Required sections (parameterized — update this list when format changes)
SECTIONS=(
  "План на сегодня"
  "Календарь"
  "Здоровье бота"
  "IWE за ночь"
  "Наработки Scout"
  "Контент-план"
  "Разбор заметок"
  "Итоги вчера"
  "Мир"
  "Контекст недели"
  "Требует внимания"
)

MISSING=()
for section in "${SECTIONS[@]}"; do
  if ! grep -q "$section" "$DAYPLAN"; then
    MISSING+=("$section")
  fi
done

# Check mandatory format elements
ERRORS=()

# Mandatory check line (WP-7 + content WP)
if ! grep -qi "mandatory" "$DAYPLAN"; then
  ERRORS+=("Mandatory check (WP-7 + контентный РП) не найден")
fi

# Budget format
if ! grep -qE "~[0-9]+\.?[0-9]*h РП" "$DAYPLAN"; then
  ERRORS+=("Бюджет дня не в формате '~Xh РП / ~Yh физ'")
fi

# Report results
if [ ${#MISSING[@]} -gt 0 ] || [ ${#ERRORS[@]} -gt 0 ]; then
  MISSING_STR=$(printf ', %s' "${MISSING[@]}")
  MISSING_STR=${MISSING_STR:2}
  ERRORS_STR=$(printf ', %s' "${ERRORS[@]}")
  ERRORS_STR=${ERRORS_STR:2}

  MSG="⛔ DAYPLAN VALIDATION FAILED."
  [ ${#MISSING[@]} -gt 0 ] && MSG="$MSG Пропущены секции (${#MISSING[@]}): $MISSING_STR."
  [ ${#ERRORS[@]} -gt 0 ] && MSG="$MSG Ошибки формата: $ERRORS_STR."
  MSG="$MSG Исправь DayPlan перед коммитом. Не коммить невалидный артефакт."

  cat <<EOF
{"decision": "block", "reason": "$MSG"}
EOF
else
  cat <<'EOF'
{"additionalContext": "✅ DayPlan прошёл валидацию: 11/11 секций, mandatory check, бюджет в формате."}
EOF
fi

exit 0
