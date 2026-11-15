"""Install or update the two KaalaiSpark cron-job.org triggers.

Credentials come from Actions secrets. Never log request headers or payloads.
"""
import json
import os
import time
import urllib.error
import urllib.request

REPOSITORY = 'PrithvirajuVenkataraman/kaalai-spark'
WORKFLOW = f'https://api.github.com/repos/{REPOSITORY}/actions/workflows/morning.yml'


def request_json(method, url, token, payload=None):
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
               'Accept': 'application/vnd.github+json' if 'api.github.com/' in url else 'application/json',
               'User-Agent': 'KaalaiSpark-Scheduler-Setup'}
    if 'api.github.com/' in url:
        headers['X-GitHub-Api-Version'] = '2022-11-28'
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as error:
        # A third-party response may contain credentials. Log only service and status.
        service = 'GitHub' if 'api.github.com/' in url else 'cron-job.org'
        raise RuntimeError(f'{service} returned HTTP {error.code}. Check credentials, permissions, and account limits.') from None
    except (OSError, ValueError):
        raise RuntimeError('Scheduler setup request failed. Rerun setup after checking the service status.') from None


def job_definitions(github_token):
    shared = {
        'enabled': False,
        'saveResponses': False,
        'url': WORKFLOW + '/dispatches',
        'requestMethod': 1,  # POST
        'requestTimeout': 30,
        'extendedData': {
            'headers': {'Authorization': 'Bearer ' + github_token,
                        'Accept': 'application/vnd.github+json',
                        'Content-Type': 'application/json',
                        'X-GitHub-Api-Version': '2022-11-28'},
            'body': json.dumps({'ref': 'main', 'inputs': {'mode': 'scheduled'}}),
        },
        'notification': {'onFailure': True, 'onFailureCount': 2,
                         'onSuccess': True, 'onDisable': True},
    }
    common_schedule = {'timezone': 'Asia/Kolkata', 'expiresAt': 0,
                       'mdays': [-1], 'months': [-1], 'wdays': [-1]}
    return [
        dict(shared, title='KaalaiSpark morning preparation and retries',
             schedule=dict(common_schedule, hours=[9], minutes=[45, 50, 55])),
        dict(shared, title='KaalaiSpark daytime recovery',
             schedule=dict(common_schedule, hours=list(range(10, 24)), minutes=list(range(0, 60, 5)))),
    ]


def configure(cron_key, github_token, api=request_json, sleeper=time.sleep):
    # Validate token access to the exact workflow before saving it at cron-job.org.
    workflow = api('GET', WORKFLOW, github_token)
    if workflow.get('state') != 'active':
        raise RuntimeError('The GitHub morning workflow must be active before installing external triggers.')
    listing = api('GET', 'https://api.cron-job.org/jobs', cron_key)
    if listing.get('someFailed'):
        raise RuntimeError('The scheduler returned an incomplete job list. No schedules were changed.')
    existing = listing.get('jobs', [])
    installed = []
    for definition in job_definitions(github_token):
        matches = [job for job in existing if job.get('title') == definition['title']]
        if len(matches) > 1:
            raise RuntimeError('Duplicate KaalaiSpark jobs exist. Remove the extra job in cron-job.org before retrying.')
        if matches:
            job_id = matches[0]['jobId']
            api('PATCH', f'https://api.cron-job.org/jobs/{job_id}', cron_key, {'job': definition})
        else:
            result = api('PUT', 'https://api.cron-job.org/jobs', cron_key, {'job': definition})
            job_id = result['jobId']
        installed.append((job_id, definition))
        sleeper(1.1)
    # Exercise the same GitHub request used by the external triggers. Daily state
    # prevents resending completed categories. The external HTTP path itself must
    # also be checked with Test run in cron-job.org after setup.
    api('POST', WORKFLOW + '/dispatches', github_token,
        {'ref': 'main', 'inputs': {'mode': 'scheduled'}})
    for job_id, definition in installed:
        api('PATCH', f'https://api.cron-job.org/jobs/{job_id}', cron_key, {'job': {'enabled': True}})
        saved = api('GET', f'https://api.cron-job.org/jobs/{job_id}', cron_key)['jobDetails']
        if not saved.get('enabled') or saved.get('schedule') != definition['schedule']:
            raise RuntimeError('Saved scheduler settings do not match. Check the scheduler dashboard.')
        print(f"Enabled and verified scheduler job {job_id}: {definition['title']}")
    print('External schedules installed. GitHub accepted the connection test.')
    print('Check the new morning run and use Test run in cron-job.org to verify external HTTP execution.')


def main():
    cron_key = os.environ.get('CRON_JOB_API_KEY', '').strip()
    github_token = os.environ.get('GH_SCHEDULER_TOKEN', '').strip()
    if not cron_key or not github_token:
        raise RuntimeError('Add CRON_JOB_API_KEY and GH_SCHEDULER_TOKEN as repository Actions secrets, then rerun setup.')
    configure(cron_key, github_token)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, KeyError) as error:
        print(str(error) if isinstance(error, RuntimeError) else 'Unexpected scheduler response. Check the dashboard before retrying.')
        raise SystemExit(1)
