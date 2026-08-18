import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest

import model_resolver
from model_resolver import resolve_grade, resolve_model


POLICY_KEY = 'profiles/vision-judgment/policy.json'
MAPPING_KEY = 'profiles/vision-judgment/mapping.json'


@pytest.fixture(autouse=True)
def catalog_env(monkeypatch):
    monkeypatch.setenv('MODEL_CATALOG_BUCKET', 'catalog-bucket')
    monkeypatch.setenv('MODEL_CATALOG_PROFILE', 'vision-judgment')
    model_resolver.clear_cache()
    yield
    model_resolver.clear_cache()


def make_s3(objects):
    s3 = MagicMock()

    def get_object(Bucket, Key):
        if Key not in objects:
            raise RuntimeError('NoSuchKey')
        return {'Body': BytesIO(json.dumps(objects[Key]).encode('utf-8'))}

    s3.get_object.side_effect = get_object
    return s3


def policy(force_high=None):
    return {'force': {'high': force_high, 'standard': None, 'low': None}}


def mapping(high='anthropic.claude-sonnet-5'):
    return {'grades': {'high': {'model_id': high}, 'standard': {'model_id': None}, 'low': {'model_id': None}}}


class TestResolveGrade:
    def test_force_takes_priority_over_mapping(self):
        model, source = resolve_grade('high', policy(force_high='claude-opus-4-8'), mapping())
        assert (model, source) == ('claude-opus-4-8', 'policy.force')

    def test_mapping_used_when_force_is_none(self):
        model, source = resolve_grade('high', policy(), mapping())
        assert (model, source) == ('anthropic.claude-sonnet-5', 'mapping')

    def test_returns_none_when_mapping_grade_is_unassigned(self):
        model, source = resolve_grade('standard', policy(), mapping())
        assert (model, source) == (None, 'fallback')

    def test_returns_none_when_documents_are_missing(self):
        assert resolve_grade('high', None, None) == (None, 'fallback')


class TestResolveModel:
    def test_resolves_via_s3_documents(self):
        s3 = make_s3({POLICY_KEY: policy(), MAPPING_KEY: mapping()})
        model, source = resolve_model('high', s3=s3, now=0.0)
        assert (model, source) == ('anthropic.claude-sonnet-5', 'mapping')

    def test_invalid_grade_returns_fallback_without_s3(self):
        s3 = make_s3({})
        assert resolve_model('premium', s3=s3, now=0.0) == (None, 'fallback')
        s3.get_object.assert_not_called()

    def test_missing_bucket_env_returns_fallback(self, monkeypatch):
        monkeypatch.delenv('MODEL_CATALOG_BUCKET')
        s3 = make_s3({})
        assert resolve_model('high', s3=s3, now=0.0) == (None, 'fallback')
        s3.get_object.assert_not_called()

    def test_s3_failure_falls_back_and_does_not_raise(self):
        s3 = make_s3({})
        assert resolve_model('high', s3=s3, now=0.0) == (None, 'fallback')

    def test_cache_prevents_repeated_reads_within_ttl(self):
        s3 = make_s3({POLICY_KEY: policy(), MAPPING_KEY: mapping()})
        resolve_model('high', s3=s3, now=0.0)
        resolve_model('low', s3=s3, now=100.0)
        assert s3.get_object.call_count == 2
        resolve_model('high', s3=s3, now=400.0)
        assert s3.get_object.call_count == 4
