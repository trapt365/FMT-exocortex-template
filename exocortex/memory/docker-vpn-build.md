---
name: Docker build fails with VPN
description: Docker container rebuild fails when VPN is active — apt can't reach debian repos. Affects projects in C:\Users\Timur\projects\
type: feedback
---

При пересборке Docker-контейнеров (devcontainer rebuild) с включённым VPN — `apt update` не может достучаться до `deb.debian.org`, билд падает.

**Why:** VPN перенаправляет трафик Docker daemon, Debian-зеркала становятся недоступны. Проблема повторяется в разных проектах из `C:\Users\Timur\projects\`.

**How to apply:** Перед любым `docker build` / Rebuild Container — напомнить отключить VPN. После успешной сборки можно включить обратно. Также: минимизировать изменения в кэшированных `RUN apt` слоях Dockerfile — добавлять новые пакеты отдельным `RUN` слоем, чтобы не инвалидировать кэш.
