"""Free public employer job-board adapters. Board names are configurable."""
import json
from pathlib import Path
from urllib.parse import quote
from jobs import fetch, clean_html

BOARDS_PATH = Path("data/job_boards.json")

def configured_boards():
    try:
        data=json.loads(BOARDS_PATH.read_text())
        return {k:v for k,v in data.items() if k in ("greenhouse","lever","ashby") and isinstance(v,list)}
    except (OSError,ValueError):
        return {}

def collect():
    results=[]
    for provider,slugs in configured_boards().items():
        for slug in slugs[:120]:
            if not isinstance(slug,str) or not slug or not all(c.isalnum() or c in "-_" for c in slug):
                continue
            q=quote(slug)
            try:
                if provider=="greenhouse":
                    payload=fetch(f"https://boards-api.greenhouse.io/v1/boards/{q}/jobs?content=true")
                    for j in payload.get("jobs",[]):
                        results.append(dict(company=slug,role=j.get("title",""),location=(j.get("location") or {}).get("name",""),
                            description=clean_html(j.get("content","")),url=j.get("absolute_url",""),salary="Not disclosed",
                            date=j.get("updated_at",""),type="",source="Greenhouse (updated time)"))
                elif provider=="lever":
                    payload=fetch(f"https://api.lever.co/v0/postings/{q}?mode=json")
                    for j in payload:
                        desc=j.get("descriptionPlain","")+" "+ " ".join(x.get("content","") for x in j.get("lists",[]))
                        results.append(dict(company=slug,role=j.get("text",""),location=(j.get("categories") or {}).get("location",""),
                            description=clean_html(desc),url=j.get("hostedUrl") or j.get("applyUrl") or "",
                            salary="Not disclosed",date="",type=(j.get("categories") or {}).get("commitment",""),
                            source="Lever (posting date unknown)"))
                elif provider=="ashby":
                    payload=fetch(f"https://api.ashbyhq.com/posting-api/job-board/{q}?includeCompensation=true")
                    for j in payload.get("jobs",[]):
                        results.append(dict(company=slug,role=j.get("title",""),location=j.get("location",""),
                            description=clean_html(j.get("descriptionPlain","")),url=j.get("applyUrl") or j.get("jobUrl") or "",
                            salary=(j.get("compensation") or {}).get("scrapeableCompensationSalarySummary") or "Not disclosed",
                            date="",type=j.get("employmentType",""),source="Ashby (posting date unknown)"))
            except (OSError,ValueError,TypeError,KeyError) as exc:
                print("Employer board unavailable:",provider,slug,type(exc).__name__,flush=True)
    return results
