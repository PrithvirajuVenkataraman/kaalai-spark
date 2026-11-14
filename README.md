# KaalaiSpark

Three short Telegram updates each morning: AI news, world/India/Tamil Nadu news, and an interesting history story.

## First connection test

1. Start your bot in Telegram.
2. Add repository Actions secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
3. Open **Actions > KaalaiSpark Morning > Run workflow**.
4. Leave **mode** as **test**, then click **Run workflow**.
5. Check Telegram for the connection message. A green run confirms Telegram accepted the message.
6. To receive the first full briefing immediately, run again with **digest**. **preview** prints a briefing to the run log without sending it.

## Schedule

The scheduler requests attempts every five minutes from 09:45 to 23:55 IST each day. The 09:45 attempt prepares the previous 24 hours of news and waits until 09:50 IST before sending. Attempts at 09:50, 09:55, 10:00 and every five minutes after that recover missing delivery. If GitHub starts an attempt late, delivery happens as soon as preparation finishes. Once all three categories are recorded as sent for the current IST date, subsequent jobs skip collection, tests, and delivery. Scheduled jobs that start before 09:45 IST are skipped. Partial delivery retries skip categories already sent. Midnight resets the daily date, so retries do not send yesterday's briefing. The schedule still creates lightweight checking jobs after success; it does not disable itself for the day. Exact start and delivery times are not guaranteed by GitHub, and multiple scheduled attempts may still be delayed or dropped. A push that changes `morning.yml` on `main` attempts today's digest as a recovery action. Scheduled workflows in public repositories may be disabled after 60 days of inactivity; check Actions if updates stop.

This program runs on GitHub, independently of your ChatGPT account, subscription, browser, and computer. It uses Python's standard library, free public feeds, Wikipedia history data, and the Telegram Bot API. No ChatGPT account, AI API key, or paid model is required. Standard GitHub-hosted runners in public repositories are free under GitHub's current policy. Free service policies can change.

## Content

- AI: up to four recent stories from TechCrunch and MIT News.
- General: up to two stories each for World, India, and Tamil Nadu. Sources include BBC, The Hindu, and a Google News fallback for Tamil Nadu.
- Headlines and short publisher excerpts with original links. These are feed-based briefs, not AI-written analysis or independently fact-checked reporting. Publication time does not necessarily equal event time. Selection is based on freshness, with similar headlines removed.
- First history story: Ray-Ban. Later stories use Wikipedia's events for the current calendar date and short background excerpts, with attribution and links. Wikipedia is a secondary source; follow its references for verification. Previously sent event IDs are retained to reduce repeats.
- An unavailable feed produces an explicit status, not invented news. A failed history lookup produces an availability notice.

## Delivery state and privacy

`data/state.json` contains delivery dates, message categories, and history event IDs, all public. It contains no bot token or chat ID. Each successful message is recorded so a repeat digest run on the same IST date skips completed categories. Keep both secrets in GitHub Actions secrets, never in files or logs. The workflow needs `contents: write` to save delivery state. If organization policy blocks that permission, allow repository workflow write access or the state-save step will fail.

Telegram has no client idempotency key. A rare timeout after acceptance, a failure during a split message, or a failed state commit can cause a duplicate on a later manual rerun. The program avoids blind retries of ambiguous Telegram failures. Preview mode never sends messages or updates state.

For local checks: `python -m unittest discover -s tests -v`. For a local preview: `python spark.py --mode preview`.

Existing ChatGPT scheduled tasks are separate. Pause them after the Telegram test succeeds if you want only Telegram delivery.
