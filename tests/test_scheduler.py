import json
import unittest
import configure_scheduler as scheduler


class SchedulerTests(unittest.TestCase):
    def test_windows_and_dispatch(self):
        jobs = scheduler.job_definitions('private-token')
        times = {(h, m) for job in jobs for h in job['schedule']['hours'] for m in job['schedule']['minutes']}
        expected = {(x // 60, x % 60) for x in range(9 * 60 + 45, 24 * 60, 5)}
        self.assertEqual(times, expected)
        for job in jobs:
            self.assertFalse(job['enabled'])
            self.assertFalse(job['saveResponses'])
            self.assertEqual(job['requestMethod'], 1)
            self.assertEqual(job['schedule']['timezone'], 'Asia/Kolkata')
            self.assertEqual(json.loads(job['extendedData']['body'])['inputs']['mode'], 'scheduled')

    def test_rerun_updates_existing_jobs_and_enables_after_test(self):
        definitions = scheduler.job_definitions('private-token')
        jobs = {i + 1: dict(job, jobId=i + 1) for i, job in enumerate(definitions)}
        calls = []
        def api(method, url, token, payload=None):
            calls.append((method, url, payload))
            if url == scheduler.WORKFLOW:
                return {'state': 'active'}
            if url.endswith('/dispatches'):
                return {}
            if url.endswith('/jobs'):
                return {'jobs': list(jobs.values())}
            job_id = int(url.rsplit('/', 1)[1])
            if method == 'PATCH':
                jobs[job_id].update(payload['job'])
                return {}
            return {'jobDetails': jobs[job_id]}
        scheduler.configure('cron-key', 'private-token', api, lambda _: None)
        self.assertFalse(any(method == 'PUT' for method, _, _ in calls))
        test_index = next(i for i, call in enumerate(calls) if call[0] == 'POST')
        enabled_indices = [i for i, (_, _, data) in enumerate(calls) if data == {'job': {'enabled': True}}]
        self.assertTrue(all(i > test_index for i in enabled_indices))

    def test_invalid_access_does_not_create_jobs(self):
        calls = []
        def api(method, url, token, payload=None):
            calls.append(method)
            return {'state': 'disabled_manually'}
        with self.assertRaises(RuntimeError):
            scheduler.configure('key', 'token', api, lambda _: None)
        self.assertEqual(calls, ['GET'])


if __name__ == '__main__':
    unittest.main()
