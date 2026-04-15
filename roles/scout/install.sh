#!/bin/bash
# Scout: установка (создание директорий в agent-workspace)
# Расписание — через scheduler.sh (не требует отдельного launchd)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${WORKSPACE:-$HOME/IWE}"
AGENT_WORKSPACE="$WORKSPACE/DS-agent-workspace"

echo "Installing Scout (R3)..."

# Проверяем agent-workspace
if [ ! -d "$AGENT_WORKSPACE" ]; then
    echo "WARN: DS-agent-workspace not found at $AGENT_WORKSPACE"
    echo "  Run: bash setup/optional/setup-agent-workspace.sh"
    echo "  Or create manually: mkdir -p $AGENT_WORKSPACE/scout/{results,trajectory}"
fi

# Создаём директории
mkdir -p "$AGENT_WORKSPACE/scout/results"
mkdir -p "$AGENT_WORKSPACE/scout/trajectory"
mkdir -p "$HOME/logs/scout"

# Делаем скрипт исполняемым
chmod +x "$SCRIPT_DIR/scripts/scout.sh"

echo "  Done: Scout directories created"
echo ""
echo "  Results:    $AGENT_WORKSPACE/scout/results/"
echo "  Trajectory: $AGENT_WORKSPACE/scout/trajectory/"
echo "  Logs:       ~/logs/scout/"
echo ""
echo "Manual run: bash $SCRIPT_DIR/scripts/scout.sh knowledge-gaps"
echo "Scheduled:  via scheduler.sh (nightly 22:00+)"
