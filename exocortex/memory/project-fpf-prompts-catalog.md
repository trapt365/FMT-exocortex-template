---
name: project-fpf-prompts-catalog
description: "Каталог FPF-промптов в Vault1/FPF Prompts/ — situation→pattern, источники R1 + ЖЖ ailev"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5db4a802-1428-48b3-b367-57f7b09397b5
---

Каталог reusable FPF-промптов «какой паттерн FPF для какой ситуации» живёт в `/mnt/c/Users/Timur/Documents/Vault1/FPF Prompts/` (Obsidian Base `FPF Prompts.base`, view-фильтр `type == fpf-prompt`).

**Критерий включения (строгий, задан Тимуром 2026-05-27):** в каталоге остаются ТОЛЬКО промпты, чей текст напрямую обращается к FPF (называет код-паттерн A.6/C.2.1/… или явно «с учётом FPF»). Промпты «общесистемного мышления» без прямого обращения к FPF удаляются.

**Структура:** каждый промпт — отдельный MD с frontmatter (`prompt_id`, `situation`, `fpf_patterns`, `fpf_pattern_doc` = wiki-link, `prompt_text`, `source_url`). Колонка Base «Документ FPF» = кликабельная ссылка на pattern-doc в `Patterns/`. Pattern-доки содержат **verbatim-выдержки из FPF-Spec.md** (`/home/trapt22/IWE/FPF/FPF-Spec.md`), НЕ интерпретации.

**Источники:** (1) R1-clippings курса «Распожаризация» в Vault1/Clippings; (2) ЖЖ ailev 2025 (посты ~1769000–1789000, FPF-эпоха). Старше 2025 FPF-промптов нет (FPF появился середина 2025).

**Состояние на 2026-05-27:** 10 промптов (P-002, P-010, P-017, P-024, P-027 из курса; P-030..P-034 из ЖЖ ailev), 9 pattern-доков (A.1, A.6, A.6.P, A.7, A.19, B.3, C.2.1, E.10, E.12). Связано с обучением [[R1+R6 Aisystant]].
