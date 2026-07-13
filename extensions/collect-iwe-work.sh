#!/bin/bash
# collect-iwe-work.sh — Ф5 WP-40: сборщик результатов работы в IWE за день.
#
# Обходит все git-репо в ~/IWE/, собирает коммиты + изменённые файлы за дату,
# пишет заметку-реестр в vault (Vault1/IWE/Работа IWE YYYY-MM-DD.md) и копирует
# снапшоты ключевых .md-артефактов в vault, чтобы они были кликабельны в Obsidian
# (вариант A, согласовано пилотом 2026-07-13).
#
# Использование:
#   collect-iwe-work.sh              # сегодня
#   collect-iwe-work.sh 2026-07-13   # конкретная дата
#   collect-iwe-work.sh --stdout-summary  # только одну строку-сводку в stdout
#
# Требует в .exocortex.env: VAULT_DIR
# see WP-40 Ф5

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.exocortex.env"
IWE_ROOT="$HOME/IWE"
MAX_SNAPSHOTS=20

[ -f "$ENV_FILE" ] && source "$ENV_FILE"
if [ -z "${VAULT_DIR:-}" ]; then echo "ERROR: VAULT_DIR не задан в $ENV_FILE" >&2; exit 1; fi

TARGET_DATE=$(date +%Y-%m-%d)
SUMMARY_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --stdout-summary) SUMMARY_ONLY=true ;;
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) TARGET_DATE="$arg" ;;
    esac
done

NOTE_DIR="$VAULT_DIR/IWE"
ATTACH_DIR="$NOTE_DIR/attachments/$TARGET_DATE"
NOTE_FILE="$NOTE_DIR/Работа IWE $TARGET_DATE.md"
mkdir -p "$ATTACH_DIR"

# Собираем сырьё по репо в temp-файл: формат строк
#   C<TAB>repo<TAB>HH:MM<TAB>subject
#   F<TAB>repo<TAB>relpath        (изменённый файл в коммитах за дату)
RAW=$(mktemp /tmp/iwe-work-XXXXX)
trap 'rm -f "$RAW"' EXIT

for repo_dir in "$IWE_ROOT"/*/; do
    [ -d "$repo_dir/.git" ] || continue
    repo=$(basename "$repo_dir")
    # Коммиты за дату (по author-date, локальное время)
    while IFS='|' read -r ts subject; do
        [ -n "$ts" ] || continue
        printf 'C\t%s\t%s\t%s\n' "$repo" "$ts" "$subject" >> "$RAW"
    done < <(git -C "$repo_dir" log --no-merges \
                --since="$TARGET_DATE 00:00:00" --until="$TARGET_DATE 23:59:59" \
                --date=format:'%H:%M' --pretty='%ad|%s' 2>/dev/null || true)
    # Изменённые файлы в этих коммитах
    while read -r f; do
        [ -n "$f" ] || continue
        printf 'F\t%s\t%s\n' "$repo" "$f" >> "$RAW"
    done < <(git -C "$repo_dir" log --no-merges \
                --since="$TARGET_DATE 00:00:00" --until="$TARGET_DATE 23:59:59" \
                --name-only --pretty='' 2>/dev/null | sort -u || true)
done

# Сборка заметки + снапшоты — на python (надёжнее для строк/файлов)
python3 - "$RAW" "$TARGET_DATE" "$IWE_ROOT" "$NOTE_FILE" "$ATTACH_DIR" "$MAX_SNAPSHOTS" "$SUMMARY_ONLY" << 'PYEOF'
import sys, os, shutil
from collections import defaultdict

raw, date, iwe_root, note_file, attach_dir, max_snap, summary_only = sys.argv[1:8]
max_snap = int(max_snap); summary_only = (summary_only == "true")

commits = defaultdict(list)   # repo -> [(time, subject)]
files = defaultdict(set)      # repo -> {relpath}
with open(raw, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if parts[0] == "C" and len(parts) >= 4:
            commits[parts[1]].append((parts[2], parts[3]))
        elif parts[0] == "F" and len(parts) >= 3:
            files[parts[1]].add(parts[2])

repos = sorted(set(commits) | set(files))
total_commits = sum(len(v) for v in commits.values())

# Снапшоты: ключевые .md из docs/ или inbox/ или корня, изменённые сегодня
SNAP_DIRS = ("docs/", "inbox/", "current/")
snapshots = []  # (repo, relpath, vault_link_name)
count = 0
for repo in repos:
    for rel in sorted(files[repo]):
        if count >= max_snap:
            break
        if not rel.endswith(".md"):
            continue
        depth_ok = rel.startswith(SNAP_DIRS) or ("/" not in rel)
        if not depth_ok:
            continue
        src = os.path.join(iwe_root, repo, rel)
        if not os.path.isfile(src):
            continue  # файл удалён/переименован
        base = os.path.basename(rel)[:-3]
        link_name = f"{repo} — {base} ({date})"
        dst = os.path.join(attach_dir, link_name + ".md")
        try:
            with open(src, encoding="utf-8") as s:
                body = s.read()
        except Exception:
            continue
        header = (f"> Зеркало для просмотра. Источник: `{repo}/{rel}` (изменён {date}). "
                  f"Не редактировать здесь — правки в репозитории.\n\n")
        with open(dst, "w", encoding="utf-8") as d:
            d.write(header + body)
        snapshots.append((repo, rel, link_name))
        count += 1

# Одна строка-сводка (для картины дня / Telegram)
summary = f"{total_commits} коммит(ов) в {len(repos)} репо" if total_commits else "коммитов нет"
if summary_only:
    print(summary)
    sys.exit(0)

lines = []
lines.append("---")
lines.append("tags:\n  - iwe-work")
lines.append(f"date: {date}")
lines.append("source: collect-iwe-work.sh (WP-40 Ф5)")
lines.append("---")
lines.append("")
lines.append(f"# Работа IWE {date}")
lines.append("")
lines.append(f"> Автосводка результатов работы в IWE за день. {summary}.")
lines.append("")
if not repos:
    lines.append("_За этот день коммитов в репозиториях IWE нет._")
for repo in repos:
    lines.append(f"## {repo}")
    lines.append("")
    for t, subj in sorted(commits[repo]):
        lines.append(f"- `{t}` {subj}")
    if not commits[repo]:
        lines.append("- _файлы изменены без коммита за эту дату_")
    # ссылки на снапшоты этого репо
    repo_snaps = [s for s in snapshots if s[0] == repo]
    if repo_snaps:
        lines.append("")
        lines.append("**Артефакты (кликабельно):**")
        for _, rel, link in repo_snaps:
            lines.append(f"- [[{link}]] — `{rel}`")
    # прочие изменённые файлы (без снапшота) — просто путь
    other = [rel for rel in sorted(files[repo]) if not any(s[1] == rel for s in repo_snaps)]
    if other:
        lines.append("")
        lines.append("<details><summary>Прочие изменённые файлы</summary>")
        lines.append("")
        for rel in other:
            lines.append(f"- `{repo}/{rel}`")
        lines.append("")
        lines.append("</details>")
    lines.append("")

os.makedirs(os.path.dirname(note_file), exist_ok=True)
with open(note_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"OK: {summary}. Заметка: {note_file}. Снапшотов: {len(snapshots)}.")
PYEOF
