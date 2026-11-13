from datetime import datetime, timedelta
import unittest
from unittest.mock import patch
import spark


class SparkTests(unittest.TestCase):
    def test_feed_filters_old_and_undated_items(self):
        xml = b'''<rss><channel>
        <item><title>New &amp; useful</title><link>https://example.com/new</link><pubDate>Fri, 13 Nov 2026 03:00:00 GMT</pubDate><description>&lt;p&gt;Short report&lt;/p&gt;</description></item>
        <item><title>Old</title><link>https://example.com/old</link><pubDate>Wed, 11 Nov 2026 03:00:00 GMT</pubDate></item>
        <item><title>Unknown date</title><link>https://example.com/no</link></item>
        </channel></rss>'''
        rows = spark.parse_feed(xml, 'Source', datetime(2026, 11, 13, 9, 45, tzinfo=spark.IST))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['summary'], 'Short report')

    def test_duplicate_stories_across_sections(self):
        item = {'title': 'A significant new discovery', 'url': 'https://example.com/a', 'published': '2026-11-13'}
        used = []
        self.assertEqual(len(spark.select_news([item], used, 2)), 1)
        self.assertEqual(spark.select_news([dict(item, url='https://other.com/a')], used, 2), [])

    def test_waits_until_ten_but_not_after(self):
        clock = [datetime(2026, 11, 13, 9, 45, tzinfo=spark.IST)]
        waits = []
        def sleep(seconds):
            waits.append(seconds)
            clock[0] += timedelta(seconds=seconds)
        spark.wait_until_delivery(lambda: clock[0], sleep)
        self.assertEqual(sum(waits), 900)
        self.assertLessEqual(max(waits), 30)
        waits.clear()
        spark.wait_until_delivery(lambda: clock[0], sleep)
        self.assertEqual(waits, [])

    def test_telegram_splitting_accounts_for_emoji(self):
        text = ('abc ' + chr(0x1F600)) * 3000
        parts = list(spark.chunks(text))
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(p.encode('utf-16-le')) // 2 <= 3500 for p in parts))

    def test_failed_delivery_does_not_expose_token(self):
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'secret-value', 'TELEGRAM_CHAT_ID': '123'}):
            with patch('urllib.request.urlopen', side_effect=OSError('URL contains secret-value')):
                with self.assertRaises(RuntimeError) as caught:
                    spark.send_telegram('hello')
        self.assertNotIn('secret-value', str(caught.exception))

    def test_first_fact_does_not_require_network(self):
        text, key = spark.fact_story(datetime.now(spark.IST), {})
        self.assertEqual(key, 'rayban')
        self.assertIn('1937', text)


if __name__ == '__main__':
    unittest.main()
