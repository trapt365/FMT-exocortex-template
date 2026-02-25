#!/bin/bash
# Extractor: установка launchd-агента для inbox-check
# Запускает inbox-check каждые 3 часа
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/scripts/launchd/com.extractor.inbox-check.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.extractor.inbox-check.plist"

echo "Installing Extractor launchd agent..."

# Проверяем что plist существует
if [ ! -f "$PLIST_SRC" ]; then
    echo "ERROR: $PLIST_SRC not found"
    exit 1
fi

# Делаем скрипт исполняемым
chmod +x "$SCRIPT_DIR/scripts/extractor.sh"

# Выгружаем старый агент (если есть)
launchctl unload "$PLIST_DST" 2>/dev/null || true

# Копируем plist
cp "$PLIST_SRC" "$PLIST_DST"

# Загружаем агент
launchctl load "$PLIST_DST"

echo "  ✓ Installed: com.extractor.inbox-check"
echo "  ✓ Interval: every 3 hours"
echo "  ✓ Logs: ~/logs/extractor/"
echo ""
echo "Verify: launchctl list | grep extractor"
echo "Uninstall: launchctl unload $PLIST_DST && rm $PLIST_DST"
