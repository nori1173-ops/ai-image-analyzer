"""ai-model-selector の mapping/policy からグレード→実モデルIDを解決する。

優先順: policy.force[grade] → mapping.grades[grade].model_id → (None, 'fallback')
S3読み取りは約5分キャッシュし、不達・不整合時は即フォールバックする（判定処理を止めない）。
"""
import json
import os
import time

GRADES = ('high', 'standard', 'low')
CACHE_TTL_SECONDS = 300

_cache = {'expires_at': 0.0, 'policy': None, 'mapping': None}
_s3_client = None


def clear_cache():
    _cache.update({'expires_at': 0.0, 'policy': None, 'mapping': None})


def resolve_grade(grade, policy, mapping):
    if isinstance(policy, dict):
        forced = (policy.get('force') or {}).get(grade)
        if isinstance(forced, str) and forced:
            return forced, 'policy.force'
    if isinstance(mapping, dict):
        entry = (mapping.get('grades') or {}).get(grade)
        model_id = entry.get('model_id') if isinstance(entry, dict) else None
        if isinstance(model_id, str) and model_id:
            return model_id, 'mapping'
    return None, 'fallback'


def _fetch_json(s3, bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception:
        return None


def _documents(s3, bucket, profile, now):
    if now < _cache['expires_at']:
        return _cache['policy'], _cache['mapping']
    prefix = f'profiles/{profile}'
    policy = _fetch_json(s3, bucket, f'{prefix}/policy.json')
    mapping = _fetch_json(s3, bucket, f'{prefix}/mapping.json')
    _cache.update({'expires_at': now + CACHE_TTL_SECONDS, 'policy': policy, 'mapping': mapping})
    return policy, mapping


def resolve_model(grade, s3=None, now=None):
    bucket = os.environ.get('MODEL_CATALOG_BUCKET', '')
    profile = os.environ.get('MODEL_CATALOG_PROFILE', 'vision-judgment')
    if grade not in GRADES or not bucket:
        return None, 'fallback'
    if s3 is None:
        global _s3_client
        if _s3_client is None:
            import boto3
            _s3_client = boto3.client('s3')
        s3 = _s3_client
    policy, mapping = _documents(s3, bucket, profile, time.time() if now is None else now)
    return resolve_grade(grade, policy, mapping)
