#!/usr/bin/env python3
# _day_picture.py — ядро сборки «картины дня» (WP-40 Ф3). Вызывается build-day-picture.sh.
# Детерминированная таблица из источников + сверка хронометража с активностью ПК
# (длительность выводится из присутствия за компом) + колонка «Тип».
# Claude добавляет только «связку» с таймаутом и откатом.
import os, re, sys, json, base64, subprocess, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

DATE   = os.environ["DP_DATE"]
NOTE   = os.environ["DP_NOTE"]
NOW_HM = os.environ["DP_NOW"]
IWE    = os.environ.get("DP_IWE", "")
CLAUDE = os.environ.get("DP_CLAUDE", "claude")
DRY    = os.environ.get("DP_DRY") == "true"
SEND_TG= os.environ.get("DP_TG") == "true"
USE_LLM= os.environ.get("DP_LLM") == "true"

day_start = datetime.fromisoformat(DATE + "T00:00:00").astimezone()
day_end   = day_start + timedelta(days=1)
now_local = datetime.now().astimezone()
now_min   = now_local.hour * 60 + now_local.minute if now_local.date() == day_start.date() else 24*60

TYPE_MAP = {"П": "Работа", "И": "Саморазвитие", "Л": "Отдых",
            "О": "Быт", "Д": "Движение", "ТО": "Быт"}
APP_RU   = {"Code.exe": "VS Code", "chrome.exe": "браузер", "Obsidian.exe": "Obsidian",
            "Telegram.exe": "Telegram", "SingularityApp.exe": "Singularity", "msedge.exe": "браузер",
            "pythonw.exe": "Anki"}
APP_TYPE = {"Code.exe": "Работа", "Obsidian.exe": "Саморазвитие", "chrome.exe": "Отдых",
            "msedge.exe": "Отдых", "Telegram.exe": "Отдых", "SingularityApp.exe": "Работа",
            "pythonw.exe": "Саморазвитие"}

def to_min(dt): return dt.astimezone().hour * 60 + dt.astimezone().minute
def hm(m):      return f"{m//60:02d}:{m%60:02d}"
def overlaps(a, b, s, e): return not (b <= s or a >= e)
def http_json(url, headers=None, t=8):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=t) as r:
        return json.load(r)

def parse_marker(text):
    m = re.search(r'\(\*?([А-Яа-яЁёA-Za-z]{1,3})\*?\)\s*$', text)
    return m.group(1).upper() if m else None

def strip_marker(text):
    return re.sub(r'\s*\(\*?[А-Яа-яЁёA-Za-z]{1,3}\*?\)\s*$', '', text).strip()

# ---------- источники ----------
def read_note_sections():
    hron, scratch = [], ""
    if os.path.isfile(NOTE):
        c = open(NOTE, encoding="utf-8").read()
        m = re.search(r'###\s*Хронометраж\s*\n(.*?)(?=\n###|\n---|\Z)', c, re.DOTALL)
        for ln in (m.group(1) if m else "").splitlines():
            # терпим необязательный маркер списка «- »/«* » перед временем
            # (сырой, ненормализованный хронометраж пишется с буллетами)
            mm = re.match(r'\s*(?:[-*]\s+)?(\d{1,2}):(\d{2})\s*[—\-]\s*(.+)', ln)
            if mm:
                t = int(mm.group(1))*60 + int(mm.group(2))
                hron.append((t, mm.group(3).strip(), parse_marker(mm.group(3))))
        m2 = re.search(r'###\s*Scratchpad\s*\n(.*?)(?=\n###|\n---|\Z)', c, re.DOTALL)
        scratch = (m2.group(1).strip() if m2 else "")
    hron.sort()
    return hron, scratch

def wakatime_blocks():
    try:
        cfg = open(os.path.expanduser("~/.wakatime.cfg"), encoding="utf-8").read()
        key = re.search(r'^\s*api_key\s*=\s*(\S+)', cfg, re.M).group(1)
        auth = base64.b64encode(f"{key}:".encode()).decode()
        data = http_json(f"https://wakatime.com/api/v1/users/current/durations?date={DATE}",
                         headers={"Authorization": "Basic " + auth}).get("data", [])
        blocks = []
        for d in sorted(data, key=lambda x: x["time"]):
            st = to_min(datetime.fromtimestamp(d["time"], tz=timezone.utc))
            en = to_min(datetime.fromtimestamp(d["time"] + d["duration"], tz=timezone.utc))
            proj = d.get("project") or "?"
            if proj == "Unknown Project": proj = "работа за компом"
            if blocks and blocks[-1][2] == proj and st - blocks[-1][1] < 12:
                blocks[-1][1] = max(blocks[-1][1], en)
            else:
                blocks.append([st, en, proj])
        return [b for b in blocks if b[1]-b[0] >= 5]
    except Exception:
        return []

def activitywatch():
    """точные оконные события [(s_min,e_min,app)] + afk-интервалы [(s,e,active)]"""
    AW = "http://localhost:5600/api/0"
    qs = urllib.parse.urlencode({"start": day_start.astimezone(timezone.utc).isoformat(),
                                 "end": day_end.astimezone(timezone.utc).isoformat()})
    win_events, afk = [], []
    try:
        buckets = http_json(f"{AW}/buckets/")
        wb = next((k for k in buckets if "window" in k), None)
        ab = next((k for k in buckets if "afk" in k), None)
        if wb:
            for e in http_json(f"{AW}/buckets/{wb}/events?{qs}"):
                app = e["data"].get("app", "?")
                if app in ("unknown", "", "LockApp.exe", "loginwindow"): continue
                st = to_min(datetime.fromisoformat(e["timestamp"]))
                win_events.append((st, st + e.get("duration", 0)/60.0, app))
        if ab:
            seen = set()
            for e in http_json(f"{AW}/buckets/{ab}/events?{qs}"):
                st = to_min(datetime.fromisoformat(e["timestamp"]))
                en = st + int(e.get("duration", 0)//60)
                if en - st < 10: continue
                key = (st, en, e["data"].get("status"))
                if key in seen: continue
                seen.add(key)
                afk.append((st, en, e["data"].get("status") == "not-afk"))
            afk.sort()
    except Exception:
        pass
    return win_events, afk

# ---------- сборка ----------
# Вариант 1: компьютер задаёт границы и длительность экранного времени,
# хронометраж (голос) навешивает ярлыки. Офлайн-время — по голосу, но ограничено
# моментом, когда снова появилась активность за компом.
MIN_SPECKLE   = 4    # мин: сегменты короче — растворяются в более длинном соседе (антидребезг)
SWITCH_MIN    = 12   # мин: молчаливое залипание в «отвлекающем» приложении длиннее — выносим отдельной строкой-догадкой
LEISURE_APPS  = ("Telegram.exe",)  # приложения, где долгое залипание без реплики трактуем как отвлечение
CAP_TAIL_MIN  = 120  # мин: последний офлайн-блок без сигналов компа не тянем дольше (не знаем, когда закончил)
PHYSICAL_MARKERS = ("Д", "ТО")  # движение/спорт, уборка/техобслуживание — не за клавиатурой, даже если окно осталось открытым

def build_rows():
    hron, scratch = read_note_sections()
    wt = wakatime_blocks()
    win_events, afk = activitywatch()

    if not (hron or win_events or wt):
        return [], scratch

    # поминутные слои за весь день [0, T1)
    T1 = max(now_min, 1)
    away = [False] * T1
    appm = [None]  * T1
    wtm  = [None]  * T1
    for s, e, act in afk:
        if act: continue
        for m in range(max(0, int(s)), min(T1, int(e))): away[m] = True
    cover = {}
    for s, e, app in win_events:
        a, b = max(0, s), min(T1, e); m = int(a)
        while m < b:
            ov = min(m + 1, b) - max(m, a)
            if ov > 0: cover.setdefault(m, {}); cover[m][app] = cover[m].get(app, 0) + ov
            m += 1
    for m, d in cover.items():
        if 0 <= m < T1: appm[m] = max(d, key=d.get)
    for s, e, p in wt:
        for m in range(max(0, int(s)), min(T1, int(e))): wtm[m] = p

    # старт картины = первая реплика (голос = точка отсчёта дня);
    # без реплик — первое реальное экранное действие. Ночной простой до этого отсекаем.
    if hron:
        T0 = max(0, min(hron[0][0], T1 - 1))
    else:
        T0 = next((m for m in range(T1) if not away[m] and (appm[m] or wtm[m])), None)
        if T0 is None:
            return [], scratch

    def keym(m):
        if away[m]:            return ("away",)
        if appm[m] is not None: return ("app", appm[m])
        if wtm[m]  is not None: return ("wt", wtm[m])
        return ("off",)

    # RLE минут в сегменты
    keys = [keym(m) for m in range(T0, T1)]
    segs, i = [], 0
    while i < len(keys):
        j = i
        while j < len(keys) and keys[j] == keys[i]: j += 1
        segs.append([T0 + i, T0 + j, keys[i]]); i = j

    # антидребезг: короткий сегмент растворяется в более длинном соседе
    changed = True
    while changed and len(segs) > 1:
        changed = False
        for idx in range(len(segs)):
            s, e, k = segs[idx]
            if e - s >= MIN_SPECKLE: continue
            left  = segs[idx-1] if idx > 0 else None
            right = segs[idx+1] if idx+1 < len(segs) else None
            if left and (not right or (left[1]-left[0]) >= (right[1]-right[0])):
                left[1] = e
            elif right:
                right[0] = s
            segs.pop(idx); changed = True; break
    m2 = []
    for s, e, k in segs:
        if m2 and m2[-1][2] == k: m2[-1][1] = e
        else: m2.append([s, e, k])
    segs = m2

    def hron_active(m):
        best = None
        for t, text, marker in hron:
            if t <= m: best = (t, text, marker)
            else: break
        return best
    def hron_in(s, e):
        return [(t, text, marker) for t, text, marker in hron if s <= t < e]

    rows = []  # (s, e, label, type, source)
    for s, e, k in segs:
        cuts = sorted(set([s, e] + [t for t, _, _ in hron_in(s, e)]))
        for a, b in zip(cuts, cuts[1:]):
            if b <= a: continue
            ut = hron_active(a)
            text   = strip_marker(ut[1]) if ut else None
            marker = ut[2] if ut else None
            own    = ut is not None and s <= ut[0] < e and ut[0] == a
            kind   = k[0]
            # окно оставлено открытым, но занятие физическое (зал, уборка) — не заявляем ПК
            if kind in ("app", "wt") and text and marker in PHYSICAL_MARKERS:
                rows.append((a, b, text, TYPE_MAP.get(marker, "Быт"), "хронометраж")); continue
            if kind == "app":
                app, app_ru = k[1], APP_RU.get(k[1], k[1])
                leisure_drift = (k[1] in LEISURE_APPS) and not own and (b - a) >= SWITCH_MIN
                if text and not leisure_drift:
                    label = text
                    typ   = TYPE_MAP.get(marker) or APP_TYPE.get(app, "—")
                    src   = f"хронометраж + ПК ({app_ru})"
                else:
                    label = f"*{app_ru} (догадка)*"
                    typ   = APP_TYPE.get(app, "—")
                    src   = "ActivityWatch"
            elif kind == "wt":
                proj = k[1]
                if text:
                    label, typ, src = text, (TYPE_MAP.get(marker) or "—"), f"хронометраж + WakaTime ({proj})"
                else:
                    label, typ, src = f"*{proj} (догадка)*", "—", "WakaTime"
            elif kind == "away":
                if text and marker in ("Л", "О", "ТО", "Д"):
                    label, typ, src = text, TYPE_MAP.get(marker, "Быт"), "хронометраж"
                else:
                    label, typ, src = "Отошёл от компьютера", "Быт", "ActivityWatch (afk)"
            else:  # off — нет следов за компом
                if text:
                    label = text
                    typ   = TYPE_MAP.get(marker) or "—"
                    src   = "хронометраж (ПК тихо)" if marker in ("П", "И") else "хронометраж"
                else:
                    label, typ, src = "Вне компьютера — данных нет", "—", "—"
            rows.append((a, b, label, typ, src))

    # склейка соседних строк с одинаковым занятием+типом
    out = []
    for r in rows:
        if out and out[-1][2] == r[2] and out[-1][3] == r[3] and r[0] - out[-1][1] <= 2:
            out[-1] = (out[-1][0], r[1], r[2], r[3], r[4])
        else:
            out.append(list(r))

    # потолок на последний офлайн-блок без сигналов компа — не тянем до полуночи
    if out:
        s, e, lbl, typ, src = out[-1]
        offline = ("ПК" not in src) and ("WakaTime" not in src)
        if offline and (e - s) > CAP_TAIL_MIN:
            out[-1] = [s, s + CAP_TAIL_MIN, lbl, typ, src]
    return out, scratch

def svyazka_fallback(rows):
    comp = [r for r in rows if "хронометраж" in r[4]]
    if not comp: return "День по измеренной активности — хронометраж пуст."
    longest = max(comp, key=lambda r: r[1]-r[0])
    return f"Крупный блок дня — {longest[2].split('(')[0].strip().lower()} ({hm(longest[0])}–{hm(longest[1])})."

def best_effort_svyazka(rows):
    if not USE_LLM: return svyazka_fallback(rows)
    table = "\n".join(f"{hm(s)}-{hm(e)} | {lbl} | {typ} | {src}" for s, e, lbl, typ, src in rows)
    prompt = ("Ниже таблица дня (время | занятие | тип | источник). Напиши ОДНУ строку — связку дня "
              "в 1-2 предложениях, живой русский, что за день сложился по-крупному (по типам активности тоже). "
              "Только строку, без префиксов.\n\n" + table)
    try:
        r = subprocess.run([CLAUDE, "--dangerously-skip-permissions", "--allowedTools", "", "-p", prompt],
                           capture_output=True, text=True, timeout=75)
        s = r.stdout.strip()
        return s.splitlines()[0] if s else svyazka_fallback(rows)
    except Exception:
        return svyazka_fallback(rows)

def render(rows, svyazka):
    lines = [f"### Картина дня (обновлено {NOW_HM})", "", f"**Связка дня:** {svyazka}", "",
             "| Время | Чем занимался | Тип | Источник |", "|-------|---------------|-----|----------|"]
    for s, e, lbl, typ, src in rows:
        lines.append(f"| {hm(s)}–{hm(e)} | {lbl} | {typ} | {src} |")
    # сводка по типам (минуты)
    agg = {}
    for s, e, lbl, typ, src in rows:
        if typ != "—": agg[typ] = agg.get(typ, 0) + (e - s)
    if agg:
        summ = " · ".join(f"{k} {v//60}ч{v%60:02d}м" for k, v in sorted(agg.items(), key=lambda x: -x[1]))
        lines += ["", f"**По типам:** {summ}"]
    lines += ["", f"**Сделано в IWE:** [[Работа IWE {DATE}]] · {IWE}"]
    return "\n".join(lines)

def seed_new_note(note_path):
    """Засев НОВОЙ daily note: шаблон Obsidian daily-note, иначе минимальная заглушка.
    Иначе cron создаёт голый файл до открытия Obsidian → шаблон не применяется → обрезанная заметка."""
    stub = "---\ntags:\n  - calendar\n---\n"
    vault = os.path.dirname(os.path.dirname(note_path))
    try:
        cfg = json.load(open(os.path.join(vault, ".obsidian", "daily-notes.json"), encoding="utf-8"))
        rel = (cfg.get("template") or "").strip()
        if rel:
            tpl = os.path.join(vault, rel if rel.endswith(".md") else rel + ".md")
            if os.path.isfile(tpl):
                return open(tpl, encoding="utf-8").read()
    except Exception:
        pass
    return stub

def write_section(section):
    os.makedirs(os.path.dirname(NOTE), exist_ok=True)
    c = open(NOTE, encoding="utf-8").read() if os.path.isfile(NOTE) else seed_new_note(NOTE)
    if "### Картина дня" in c:
        c = re.sub(r'###\s*Картина дня.*?(?=\n###|\n---\n|\Z)', section + "\n\n", c, count=1, flags=re.DOTALL)
    elif "### Хронометраж" in c:
        c = c.replace("### Хронометраж", section + "\n\n### Хронометраж", 1)
    else:
        c = c.rstrip() + "\n\n" + section + "\n"
    open(NOTE, "w", encoding="utf-8").write(c)

def send_telegram(rows, svyazka):
    secrets = os.path.expanduser("~/.secrets/tagping-telegram.env")
    token, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if os.path.isfile(secrets):
        for ln in open(secrets):
            ln = ln.strip()
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1); k, v = k.strip(), v.strip().strip('"')
                if k == "TG_BOT_TOKEN" and not token: token = v
                if k == "TG_CHAT_ID"  and not chat:  chat = v
    if not token or not chat:
        print("  Telegram: креды не найдены"); return
    agg = {}
    for s, e, lbl, typ, src in rows:
        if typ != "—": agg[typ] = agg.get(typ, 0) + (e - s)
    types = " · ".join(f"{k} {v//60}ч{v%60:02d}м" for k, v in sorted(agg.items(), key=lambda x: -x[1])[:4])
    gaps = [r for r in rows if r[4] == "—"]
    txt = f"🗓 Картина дня {NOW_HM}\n{svyazka}"
    if types: txt += f"\nПо типам: {types}"
    if gaps:  txt += "\nПробелы: " + ", ".join(f"{hm(s)}–{hm(e)}" for s, e, *_ in gaps[:3])
    txt += f"\nСделано в IWE: {IWE}"
    try:
        data = json.dumps({"chat_id": chat, "text": txt}).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data,
            headers={"Content-Type": "application/json"}), timeout=8)
        print("  Telegram: дайджест отправлен")
    except Exception as ex:
        print(f"  Telegram: ошибка {type(ex).__name__}")

def main():
    rows, scratch = build_rows()
    if not rows:
        print("Нет данных для картины дня."); return
    svyazka = best_effort_svyazka(rows)
    section = render(rows, svyazka)
    if DRY:
        print(section); print("\n[dry-run] без записи и Telegram"); return
    write_section(section)
    print(f"  Картина дня записана: {NOTE}")
    if SEND_TG: send_telegram(rows, svyazka)
    print(f"Готово: картина дня за {DATE}.")

if __name__ == "__main__":
    main()
