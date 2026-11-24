"""Free Telegram morning digest. Python standard library only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
STATE_PATH = Path('data/state.json')
AGENT = 'KaalaiSpark/1.0 (https://github.com/PrithvirajuVenkataraman/kaalai-spark)'
FEEDS = {
    'AI': [
        ('TechCrunch', 'https://techcrunch.com/category/artificial-intelligence/feed/'),
        ('MIT News', 'https://news.mit.edu/rss/topic/artificial-intelligence2'),
    ],
    'World': [('BBC', 'https://feeds.bbci.co.uk/news/world/rss.xml')],
    'India': [
        ('The Hindu', 'https://www.thehindu.com/news/national/feeder/default.rss'),
        ('BBC', 'https://feeds.bbci.co.uk/news/world/asia/india/rss.xml'),
    ],
    'Tamil Nadu': [
        ('The Hindu', 'https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss'),
        ('Google News', 'https://news.google.com/rss/search?q=Tamil+Nadu+when:1d&hl=en-IN&gl=IN&ceid=IN:en'),
    ],
}


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean(value):
    parser = TextOnly()
    parser.feed(unescape(value or ''))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip().replace('\u2014', '. ')


def clip(value, words=28, chars=220):
    text = clean(value)
    short = ' '.join(text.split()[:words])
    if len(short) > chars:
        short = short[:chars].rsplit(' ', 1)[0]
    return short + ('…' if short != text else '')


def get_bytes(url):
    request = urllib.request.Request(url, headers={'User-Agent': AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(3_000_001)
                if len(data) > 3_000_000:
                    raise ValueError('Response too large')
                return data
        except (OSError, ValueError):
            if attempt == 2:
                raise RuntimeError('Public source unavailable') from None
            time.sleep(1 + attempt)


def parse_feed(data, source, now):
    root = ET.fromstring(data)
    items = []
    for node in root.findall('.//item'):
        title = clean(node.findtext('title'))
        url = (node.findtext('link') or '').strip()
        try:
            published = parsedate_to_datetime(node.findtext('pubDate') or '')
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if not now - timedelta(hours=24) <= published <= now + timedelta(minutes=5):
            continue
        if not title or not url.startswith('https://'):
            continue
        items.append({'title': title, 'url': url, 'source': source,
                      'summary': clip(node.findtext('description')),
                      'published': published.isoformat()})
    return items


def fetch_feed(pair, now):
    source, url = pair
    try:
        return parse_feed(get_bytes(url), source, now)
    except (RuntimeError, ET.ParseError):
        print('Feed unavailable: ' + source, flush=True)
        return []


def select_news(items, used, limit):
    result = []
    for item in sorted(items, key=lambda x: x['published'], reverse=True):
        key = re.sub(r'\W+', ' ', item['title'].lower()).strip()
        if any(item['url'] == u or SequenceMatcher(None, key, t).ratio() > .78
               for u, t in used):
            continue
        used.append((item['url'], key))
        result.append(item)
        if len(result) >= limit:
            break
    return result


def section(name, items):
    lines = [name]
    if not items:
        return name + '\nNo recent items could be verified from the available feeds.'
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {clip(item['title'], 28, 180)} ({item['source']})")
        if item['summary'] and not item['summary'].startswith(item['title']):
            lines.append(item['summary'])
        lines.append(item['url'])
    return '\n'.join(lines)


def fact_story(now, state):
    if not state.get('rayban_sent'):
        return (
            'Why Ray-Ban?\n\n'
            'The name describes the purpose: to ban, or block, the sun\'s rays. '
            'Ray-Ban began with sunglasses developed by Bausch & Lomb for pilots. '
            'At higher altitudes, strong glare made flying uncomfortable. '
            'The familiar Aviator design reached the public in 1937. Its large lenses '
            'helped cover the eyes while its thin metal frame kept the glasses light. '
            'The brand later moved beyond aviation, including the Wayfarer in 1952. '
            'So the name began as a simple statement of function before it became a fashion name.\n\n'
            'Sources:\nhttps://en.wikipedia.org/wiki/Ray-Ban\n'
            'https://www.ray-ban.com/usa/ray-ban-glasses-history', 'rayban')
    # Date-specific history provides new topics without a paid model or fixed fact bank.
    url = f'https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{now:%m/%d}'
    try:
        events = json.loads(get_bytes(url)).get('events', [])
        previous = set(state.get('fact_ids', []))
        candidates = [e for e in events if f"{e.get('year')}:{e.get('text')}" not in previous]
        if not candidates:
            raise ValueError('No unused event')
        # Prefer inventions, discoveries and cultural history when present.
        keywords = ('invent', 'discover', 'patent', 'first', 'launch', 'publish', 'science')
        candidates.sort(key=lambda e: -sum(k in e.get('text', '').lower() for k in keywords))
        event = candidates[0]
        fact_id = f"{event.get('year')}:{event.get('text')}"
        text = f"On this day in {event['year']}\n\n{clean(event['text'])}"
        pages = event.get('pages', [])
        source_links = []
        if pages:
            page = pages[0]
            extract = page.get('extract', '')
            if extract:
                text += '\n\nBackground: ' + clip(extract, 65, 500)
            page_url = page.get('content_urls', {}).get('desktop', {}).get('page')
            if page_url and page_url.startswith('https://'):
                source_links.append(page_url)
        source_links.append(f'https://en.wikipedia.org/wiki/{now:%B}_{now.day}')
        text += '\n\nSource: Wikipedia (CC BY-SA).\n' + '\n'.join(source_links)
        return text, fact_id
    except (RuntimeError, ValueError, KeyError, TypeError):
        return ('The history source is unavailable today. No unverified fact was substituted.', None)


def build_digest(now, state):
    pairs = [pair for feeds in FEEDS.values() for pair in feeds]
    with ThreadPoolExecutor(max_workers=7) as pool:
        fetched = dict(zip((url for _, url in pairs), pool.map(lambda p: fetch_feed(p, now), pairs)))
    used = []
    sections = {}
    # Select local news first to prevent national coverage consuming all local stories.
    for category in ['Tamil Nadu', 'India', 'World', 'AI']:
        items = [item for _, url in FEEDS[category] for item in fetched[url]]
        sections[category] = section(category, select_news(items, used, 4 if category == 'AI' else 2))
    stamp = now.strftime('%d %b %Y, %I:%M %p IST')
    fact, fact_id = fact_story(now, state)
    return [
        ('ai', 'KaalaiSpark | AI news\n' + stamp + '\n\n' + sections['AI'], None),
        ('news', 'KaalaiSpark | News\n' + stamp + '\n\n' + '\n\n'.join(sections[k] for k in ['World', 'India', 'Tamil Nadu']), None),
        ('fact', 'KaalaiSpark | Interesting story\n\n' + fact, fact_id),
    ]


def chunks(text, limit=3500):
    # UTF-16 units conservatively account for Telegram's length limit.
    current = ''
    for line in text.splitlines(keepends=True):
        while len(line.encode('utf-16-le')) // 2 > limit:
            if current:
                yield current.rstrip()
                current = ''
            piece = line[:limit // 2]
            yield piece
            line = line[len(piece):]
        if len((current + line).encode('utf-16-le')) // 2 > limit:
            yield current.rstrip()
            current = ''
        current += line
    if current.strip():
        yield current.rstrip()


def send_telegram(text):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat:
        raise RuntimeError('Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in Actions secrets.')
    for part in chunks(text):
        payload = json.dumps({'chat_id': chat, 'text': part,
                              'link_preview_options': {'is_disabled': True}}).encode()
        request = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                                         data=payload, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            if not result.get('ok'):
                raise ValueError()
        except (OSError, ValueError):
            # Do not print the URL: it contains the bot credential. Do not blindly retry
            # an ambiguous timeout, because Telegram has no idempotency key.
            raise RuntimeError('Telegram delivery failed. Check the token, chat ID, and whether you started the bot. No automatic resend was attempted.') from None
        time.sleep(1)


def load_state():
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(STATE_PATH)


def wait_until_delivery(now_func=lambda: datetime.now(IST), sleeper=time.sleep):
    now = now_func()
    target = now.replace(hour=9, minute=50, second=0, microsecond=0)
    while now < target:
        sleeper(min(30, (target - now).total_seconds()))
        now = now_func()


def delivery_complete(state, now):
    return (state.get('delivery_date') == now.date().isoformat()
            and {'ai', 'news', 'fact'}.issubset(state.get('sent', [])))


def skip_attempt(state, now, event, mode):
    if mode != 'digest':
        return False
    if event == 'schedule' and (now.hour, now.minute) < (9, 45):
        return True
    return delivery_complete(state, now)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['test', 'preview', 'digest'], default='preview')
    parser.add_argument('--wait-until-delivery', action='store_true')
    args = parser.parse_args()
    if args.mode == 'test':
        send_telegram('KaalaiSpark is connected. Your daily AI, news, and history updates will target 9:50 AM IST. This test does not change your daily delivery state.')
        print('Telegram test delivered.')
        return
    now = datetime.now(IST)
    state = load_state()
    if skip_attempt(state, now, os.environ.get('EVENT_NAME', ''), args.mode):
        print('No delivery needed for this attempt.')
        return
    messages = build_digest(now, state)
    if args.mode == 'preview':
        for _, message, _ in messages:
            print(message + '\n\n')
        return
    if args.wait_until_delivery:
        wait_until_delivery()
    if datetime.now(IST).date() != now.date():
        raise RuntimeError('Prepared digest expired. Run again for the current date.')
    today = now.date().isoformat()
    if state.get('delivery_date') != today:
        state['delivery_date'] = today
        state['sent'] = []
    for key, message, fact_id in messages:
        if key in state.get('sent', []):
            print('Already delivered today: ' + key)
            continue
        send_telegram(message)
        state.setdefault('sent', []).append(key)
        if fact_id == 'rayban':
            state['rayban_sent'] = True
        elif fact_id:
            state['fact_ids'] = (state.get('fact_ids', []) + [fact_id])[-1000:]
        save_state(state)
        print('Delivered: ' + key)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        print(str(error), flush=True)
        raise SystemExit(1)
