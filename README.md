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

The daily cron is 04:15 UTC, which is 09:45 IST. The program collects the preceding 24 hours of feed items and prepares three messages. It waits until 10:00 IST before sending. If GitHub starts the job late, it sends as soon as preparation finishes. Exact collection and delivery times are not guaranteed. Backup attempts run at 10:05, 10:45, 11:45, 12:45, and 13:45 IST. Once all three messages have been recorded as sent for the day, backup jobs exit without collecting or sending again. A push that changes `morning.yml` on `main` also attempts today's digest as a recovery action. A missing scheduled run has no application log; backup schedules reduce risk but cannot guarantee delivery if GitHub scheduling is unavailable. Public-repository scheduled workflows can be disabled after 60 days without repository activity; successful delivery-state commits normally provide activity, but check Actions if updates stop.

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
