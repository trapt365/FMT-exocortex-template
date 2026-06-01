---
name: CRM batch-outreach — одна строка ACTIVITIES на компанию
description: При массовой рассылке (демо+компред+и т.д. одним сообщением) — ОДНА строка в ACTIVITIES с объединёнными Notes, не несколько
type: feedback
valid_from: 2026-04-22
originSessionId: 542220c5-7645-4848-b899-f904a477a561
---
При batch-outreach (массовая рассылка Игоря: демо+лендинг+компред одним сообщением) = **одна строка в ACTIVITIES на компанию** с объединёнными Notes «Отправил: демо (лендинг+видео) + компред с рассрочкой. Batch <tag>».

**Why:** 22 апр я сделал 2 строки на компанию (62 строки на 31 компанию) — пользователь назвал это дубликатами, пришлось писать `undoIgorBatch` + переимпортировать. Визуально 2 строки с одинаковыми Date/Type/Direction/Result выглядят как дубль, даже если Notes разные.

**How to apply:**
- Если Игорь (или любой) отправил «всё сразу» одним сообщением → 1 активность в CRM.
- Несколько активностей = только если это реально разные контакты в разное время (звонок + email + встреча).
- Activity_Type = первый канал (WhatsApp по умолчанию, Email если «на почту»).
- Direction=Исходящий (русск., не Outbound — data validation LOOKUP на русских значениях).
- Result=Не ответил (НЕ «Нет ответа» — в LOOKUP такого нет).
- Всегда читать headers ACTIVITIES live: `sheet.getRange(1,1,1,sheet.getLastColumn()).getValues()[0]` — локальные `crm-sheets-setup.gs` могут отставать от live схемы (напр. Company_Name + Contact_Name добавлены позже).

**Где применимо:** любой batch-import через Apps Script в DIEGE CRM (WP-17 diesel-gen).
