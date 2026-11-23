"""Conservative worldwide full-time job discovery. No paid API or credentials."""
from datetime import datetime, timedelta, timezone
import json
import re
import urllib.request

AGENT = "KaalaiSpark/1.0"
BAD = re.compile(r"\b(contract|contractor|freelance|internship|intern|part.time|temporary|seasonal|commission.only)\b", re.I)
SKILLS = re.compile(r"\b(data analyst|data quality|quality analyst|llm|ai evaluation|model evaluation|ai operations|data operations|analytics engineer|business intelligence|python developer|sql analyst|annotation quality|ai trainer)\b", re.I)
SENIOR = re.compile(r"\b(senior|staff|principal|lead|director|head of|manager|architect)\b", re.I)
EXPERIENCE = re.compile(r"\b([4-9]|1[0-9])\s*\+?\s*(?:years|yrs)\b", re.I)
NIGHT = re.compile(r"\b(night shift|overnight|graveyard|us shift|est hours|pst hours|pacific time hours|american working hours)\b", re.I)
DAY = re.compile(r"\b(flexible (?:working )?hours|async(?:hronous)?|india (?:standard )?time|ist (?:working )?hours|india daytime|work your own hours)\b", re.I)
INDIA = re.compile(r"\b(india|india-based|based in india|remote from india)\b", re.I)
SPONSOR = re.compile(r"\b(visa sponsorship (?:is )?(?:available|provided|offered)|sponsor (?:a |your )?(?:work )?visa|work visa sponsorship)\b", re.I)
RELOCATE = re.compile(r"\b(relocation (?:assistance|support|package) (?:is )?(?:available|provided|offered|included)|visa and relocation support|relocation expenses covered)\b", re.I)
NO_SPONSOR = re.compile(r"\b(no visa sponsorship|cannot sponsor|sponsorship not available|without sponsorship)\b", re.I)

def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=18) as response:
        return json.load(response)

def clean_html(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value or "")).strip()

def normalize(raw, source):
    if source == "remotive":
        return dict(company=raw.get("company_name",""), role=raw.get("title",""), location=raw.get("candidate_required_location",""),
                    description=clean_html(raw.get("description","")), url=raw.get("url",""),
                    salary=raw.get("salary") or "Not disclosed", date=raw.get("publication_date",""),
                    type=raw.get("job_type",""), source="Remotive")
    return dict(company=raw.get("company_name",""), role=raw.get("title",""), location=raw.get("location",""),
                description=clean_html(raw.get("description","")), url=raw.get("url",""),
                salary="Not disclosed", date=raw.get("created_at",""), type="",
                visa_flag=raw.get("visa_sponsorship",False), source="Arbeitnow")

def qualify(j, now):
    title=j["role"]; body=j["description"]; location=j["location"]
    if not j["company"] or not title or not j["url"].startswith("https://"):
        return None
    if not SKILLS.search(title) or BAD.search(title) or BAD.search(j["type"]):
        return None
    if SENIOR.search(title) or EXPERIENCE.search(body[:10000]):
        return None
    if re.search(r"\b(part.time|contract|freelance|temporary|internship)\b", body[:1800], re.I):
        return None
    if j["type"] and "full" not in j["type"].lower():
        return None
    try:
        stamp=datetime.fromisoformat(j["date"].replace("Z","+00:00"))
        if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
        if not now-timedelta(days=14) <= stamp <= now+timedelta(hours=1): return None
    except (ValueError, AttributeError):
        return None
    if NO_SPONSOR.search(body):
        visa=False
    else:
        visa=bool(SPONSOR.search(body))
    relocation=visa and bool(RELOCATE.search(body))
    remote_india=bool(INDIA.search(location)) and bool(DAY.search(body)) and not NIGHT.search(body)
    # Location must explicitly name India. "Worldwide" alone is not enough.
    # Relocation requires affirmative evidence for both sponsorship and assistance.
    if remote_india:
        path="Remote from India, daytime/flexible hours stated"
    elif relocation and not re.search(r"\bindia only\b",body,re.I):
        path="Relocation and visa support stated; India applicant eligibility needs confirmation"
    else:
        return None
    j["path"]=path
    j["posted"]=stamp
    return j

def find_jobs(now, seen, limit=5):
    raw=[]
    sources=[
        ("remotive","https://remotive.com/api/remote-jobs?limit=300"),
        ("arbeitnow","https://www.arbeitnow.com/api/job-board-api"),
    ]
    for name,url in sources:
        try:
            data=fetch(url)
            raw.extend((name, item) for item in (data.get("jobs",[]) if name=="remotive" else data.get("data",[])))
        except (OSError,ValueError,TypeError) as exc:
            print("Jobs source unavailable:", name, type(exc).__name__, flush=True)
    candidates=[]
    for source,item in raw:
        j=qualify(normalize(item,source),now)
        if j and j["url"].rstrip("/") not in seen:
            candidates.append(j)
    candidates.sort(key=lambda j:j["posted"],reverse=True)
    results=[]; used=set()
    for j in candidates:
        key=(j["company"].casefold(),j["role"].casefold())
        if key in used: continue
        used.add(key); results.append(j)
        if len(results)==limit: break
    return results

def build_message(now, seen):
    jobs=find_jobs(now,seen)
    lines=["KaalaiSpark | Global full-time jobs",now.strftime("%d %b %Y, %I:%M %p IST"),""]
    if not jobs:
        lines.append("No new jobs met all strict evidence checks today. No unverified roles were substituted.")
    for i,j in enumerate(jobs,1):
        lines.extend([f"{i}. {j['role']} | {j['company']}",
                      f"Location: {j['location']}",
                      f"Type: {j['path']}",
                      f"Salary: {j['salary']}",
                      f"Posted: {j['posted'].strftime('%d %b %Y %H:%M UTC')}",
                      f"Source: {j['source']} (description-based checks; confirm with employer)",
                      f"Apply: {j['url']}",""])
    return "\n".join(lines),[j["url"].rstrip("/") for j in jobs]
