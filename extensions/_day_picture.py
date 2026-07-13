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
            "Telegram.exe": "Telegram", "SingularityApp.exe": "Singularity", "msedge.exe": "браузер"}
APP_TYPE = {"Code.exe": "Работа", "Obsidian.exe": "Саморазвитие", "chrome.exe": "Отдых",
            "msedge.exe": "Отдых", "Telegram.exe": "Отдых", "SingularityApp.exe": "Работа"}

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
            mm = re.match(r'\s*(\d{1,2}):(\d{2})\s*[—\-]\s*(.+)', ln)
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
def norm_key(text):
    t = re.sub(r'\(.*?\)', '', text.lower())
    t = re.sub(r'продолжа\w*|дальше|ещё|начал[а]?|работаю над|работа над', '', t)
    t = re.sub(r'[^\wа-яё ]', ' ', t)
    return " ".join(w for w in t.split() if len(w) > 2)[:40]

def build_rows():
    hron, scratch = read_note_sections()
    wt = wakatime_blocks()
    win_events, afk = activitywatch()
    away = [(s, e) for s, e, act in afk if not act]
    active = [(s, e) for s, e, act in afk if act]
    def presence(s, e): return sum(max(0, min(ae, e) - max(a, s)) for a, ae in active)

    def app_dom(s, e):
        """доминирующее реально активное окно в [s,e] с порогом покрытия ≥40%"""
        tot = {}
        for ws, we, app in win_events:
            ov = min(we, e) - max(ws, s)
            if ov > 0: tot[app] = tot.get(app, 0) + ov
        if not tot: return None
        app = max(tot, key=tot.get)
        return app if (tot[app] >= 0.4 * (e - s) and tot[app] >= 4) else None
    def wt_cov(s, e): return sum(max(0, min(we, e) - max(ws, s)) for ws, we, p in wt)
    def wt_proj(s, e):
        ps = {}
        for ws, we, p in wt:
            ov = min(we, e) - max(ws, s)
            if ov > 0: ps[p] = ps.get(p, 0) + ov
        return max(ps, key=ps.get) if ps else None

    # backbone из хронометража
    backbone = []
    for i, (t, text, marker) in enumerate(hron):
        end = hron[i+1][0] if i+1 < len(hron) else now_min
        if end <= t: end = t + 1
        key = norm_key(text)
        cont = bool(re.match(r'\s*продолжа', text.lower()))
        if backbone and (backbone[-1][3] == key or cont) and t - backbone[-1][1] <= 120:
            backbone[-1][1] = end
        else:
            backbone.append([t, end, strip_marker(text), key, marker])

    rows = []  # (s, e, label, type, source)
    for s, e, text, key, marker in backbone:
        is_comp = (marker in ("П", "И")) or (marker is None and presence(s, e) >= 0.4 * (e - s))
        # сверка с ПК: вырезаем отлучки (afk ≥15м) из рабочих блоков → реальная длительность
        segs = [(s, e, "comp" if is_comp else "off")]
        if is_comp:
            cuts = sorted((max(a, s), min(b, e)) for a, b in away if min(b, e) - max(a, s) >= 15)
            if cuts:
                segs, cur = [], s
                for a, b in cuts:
                    if a > cur: segs.append((cur, a, "comp"))
                    segs.append((a, b, "away"))
                    cur = b
                if cur < e: segs.append((cur, e, "comp"))
        for ss, ee, kind in segs:
            if ee - ss < 1: continue
            if kind == "away":
                rows.append((ss, ee, "Отошёл от компьютера", "Быт", "ActivityWatch (afk)"))
                continue
            app = app_dom(ss, ee)
            pres = presence(ss, ee) / max(1, ee - ss)
            typ = TYPE_MAP.get(marker) or (APP_TYPE.get(app or "", "—") if app else "—")
            comp = marker in ("П", "И") or (marker is None and pres >= 0.4)
            if comp:
                if app and pres >= 0.4:
                    src = f"хронометраж + ПК ({APP_RU.get(app, app)})"
                elif wt_cov(ss, ee) >= 0.5 * (ee - ss):
                    src = f"хронометраж + WakaTime ({wt_proj(ss, ee)})"
                else:
                    src = "хронометраж (ПК тихо)"
            else:  # оффлайн-активность по хронометражу
                src = (f"хронометраж · ПК активен ({APP_RU.get(app, app)})"
                       if pres >= 0.6 and app else "хронометраж")
            rows.append((ss, ee, text, typ, src))

    # промежутки (лакуны) → догадки из активного окна / WakaTime, иначе «вне компа»
    covered = [(r[0], r[1]) for r in rows]
    def is_cov(a, b): return any(overlaps(a, b, s, e) for s, e in covered)
    activity_start = hron[0][0] if hron else (min([b[0] for b in wt]) if wt else now_min)
    m = (activity_start//30)*30
    gaps = []
    while m < now_min:
        nxt = m + 30
        if not is_cov(m, nxt): gaps.append((m, min(nxt, now_min)))
        m = nxt
    merged = []
    for g in gaps:
        if merged and g[0] - merged[-1][1] <= 0: merged[-1] = (merged[-1][0], g[1])
        else: merged.append(list(g))
    for s, e in merged:
        app = app_dom(s, e)
        if app:
            rows.append((s, e, f"*{APP_RU.get(app, app)} (догадка)*", APP_TYPE.get(app, "—"), "ActivityWatch"))
        elif wt_cov(s, e) >= 0.5 * (e - s):
            rows.append((s, e, f"*{wt_proj(s, e)} (догадка)*", "—", "WakaTime"))
        else:
            rows.append((s, e, "Вне компьютера — данных нет", "—", "—"))

    rows.sort()
    out = []
    for r in rows:
        if out and out[-1][2] == r[2] and out[-1][3] == r[3] and r[0]-out[-1][1] <= 5:
            out[-1] = (out[-1][0], r[1], r[2], r[3], r[4])
        else:
            out.append(list(r))
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

def write_section(section):
    os.makedirs(os.path.dirname(NOTE), exist_ok=True)
    c = open(NOTE, encoding="utf-8").read() if os.path.isfile(NOTE) else "---\ntags:\n  - calendar\n---\n"
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
