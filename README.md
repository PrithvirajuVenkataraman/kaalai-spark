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


## External scheduler integration

The repository is ready for cron-job.org; external schedules are NOT active until setup succeeds. Built-in GitHub schedules remain as fallback until the external path has been tested.

### One-time private account setup

1. Create or sign in to your free cron-job.org account. In Settings generate an API key. Add it to this repository's Actions secrets as `CRON_JOB_API_KEY`.
2. In GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens, create a token restricted to **PrithvirajuVenkataraman/kaalai-spark** with repository **Actions: Read and write** only (plus automatic metadata access). Choose an expiry date and record a reminder to renew it. Add it to Actions secrets as `GH_SCHEDULER_TOKEN`. Never send either key in chat or put it in repository files.
3. Open Actions > **Set Up External Scheduler** > Run workflow on main. This sends the restricted GitHub token to your cron-job.org account as an Authorization header, so that service can start only the permitted workflow operations on this repository. Your Telegram token and chat ID remain in GitHub and are not shared with cron-job.org. The cron-job.org API key remains in Actions secrets for future setup or updates.
4. Setup validates GitHub access, creates or updates two initially disabled jobs, tests a GitHub dispatch, enables both jobs, and reads their settings back. It prints job IDs and success states only. If setup fails, inspect the scheduler dashboard before rerunning; one job could already be active. Reruns update matching titles rather than adding duplicate jobs.
5. In cron-job.org, use **Test run** on the morning job. Verify a new GitHub morning run completes. An HTTP success at the scheduler means GitHub accepted a trigger, not that news was delivered. Verify the Actions job and the delivery state separately. If today was already delivered, the test correctly skips sending duplicates.

Two jobs cover **09:45, 09:50, 09:55 IST**, then **every five minutes from 10:00 to 23:55 IST**. External requests use the `scheduled` mode. The 09:45 request collects news and waits until 09:50 to send. Later requests skip work after all categories are sent. Manual `digest` sends immediately, and `test` only sends the connection message.

The external scheduler avoids GitHub's native cron trigger. GitHub runner queues, external scheduling outages, source outages, and token expiry can still delay or prevent delivery. This setup has no exact-minute delivery guarantee. Review cron-job.org execution history and notification settings if updates stop. Setup enables failure/recovery notifications using that account's configured notification channels; these report trigger-request failures, not downstream GitHub job failures.

Renew an expired GitHub token by replacing `GH_SCHEDULER_TOKEN` and rerunning setup, which updates the headers saved in both external jobs.
