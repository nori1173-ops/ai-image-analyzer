import json
import pytest
from unittest.mock import MagicMock, patch, call


MOCK_SECRET_ARN = 'arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:test-api-key'
MOCK_TOKEN = 'test-rotation-token-12345'
MOCK_USAGE_PLAN_ID = 'usage-plan-123'
MOCK_REST_API_ID = 'api-123'
MOCK_RESOURCE_PREFIX = 'image-analysis-api'


def _make_secret_value(api_key_id: str = 'old-key-id', api_key_value: str = 'old-key-value') -> str:
    return json.dumps({
        'apiKeyId': api_key_id,
        'apiKeyValue': api_key_value,
        'usagePlanId': MOCK_USAGE_PLAN_ID,
        'restApiId': MOCK_REST_API_ID,
        'stageName': 'prod',
        'resourcePrefix': MOCK_RESOURCE_PREFIX,
    })


@pytest.fixture
def sm_client():
    return MagicMock()


@pytest.fixture
def ag_client():
    return MagicMock()


@pytest.fixture
def rotation_event():
    return {
        'SecretId': MOCK_SECRET_ARN,
        'ClientRequestToken': MOCK_TOKEN,
        'Step': 'createSecret',
    }


class TestCreateSecret:
    def test_create_new_api_key(self, sm_client, ag_client):
        from rotation import create_secret

        sm_client.get_secret_value.side_effect = sm_client.exceptions.ResourceNotFoundException
        sm_client.exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        sm_client.get_secret_value.side_effect = sm_client.exceptions.ResourceNotFoundException()

        current_secret = _make_secret_value()
        sm_client.get_secret_value.side_effect = [
            sm_client.exceptions.ResourceNotFoundException(),
            {'SecretString': current_secret},
        ]

        ag_client.create_api_key.return_value = {
            'id': 'new-key-id',
            'value': 'new-key-value',
        }

        create_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        ag_client.create_api_key.assert_called_once()
        sm_client.put_secret_value.assert_called_once()
        put_call = sm_client.put_secret_value.call_args
        secret_data = json.loads(put_call.kwargs.get('SecretString', put_call[1].get('SecretString', '')))
        assert secret_data['apiKeyId'] == 'new-key-id'
        assert secret_data['apiKeyValue'] == 'new-key-value'

    def test_skip_if_pending_exists(self, sm_client, ag_client):
        from rotation import create_secret

        sm_client.get_secret_value.return_value = {
            'SecretString': _make_secret_value('pending-key-id', 'pending-key-value'),
        }

        create_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        ag_client.create_api_key.assert_not_called()
        sm_client.put_secret_value.assert_not_called()


class TestSetSecret:
    def test_create_usage_plan_key(self, sm_client, ag_client):
        from rotation import set_secret

        pending_secret = _make_secret_value('new-key-id', 'new-key-value')
        sm_client.get_secret_value.return_value = {'SecretString': pending_secret}

        set_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        ag_client.create_usage_plan_key.assert_called_once_with(
            usagePlanId=MOCK_USAGE_PLAN_ID,
            keyId='new-key-id',
            keyType='API_KEY',
        )


class TestTestSecret:
    def test_verify_api_key_enabled(self, sm_client, ag_client):
        from rotation import test_secret

        pending_secret = _make_secret_value('new-key-id', 'new-key-value')
        sm_client.get_secret_value.return_value = {'SecretString': pending_secret}
        ag_client.get_api_key.return_value = {'id': 'new-key-id', 'enabled': True}

        test_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        ag_client.get_api_key.assert_called_once_with(apiKey='new-key-id', includeValue=False)

    def test_raise_if_key_disabled(self, sm_client, ag_client):
        from rotation import test_secret

        pending_secret = _make_secret_value('new-key-id', 'new-key-value')
        sm_client.get_secret_value.return_value = {'SecretString': pending_secret}
        ag_client.get_api_key.return_value = {'id': 'new-key-id', 'enabled': False}

        with pytest.raises(ValueError, match='not enabled'):
            test_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)


class TestFinishSecret:
    def test_update_version_stage(self, sm_client, ag_client):
        from rotation import finish_secret

        sm_client.describe_secret.return_value = {
            'VersionIdsToStages': {
                'old-token': ['AWSCURRENT'],
                MOCK_TOKEN: ['AWSPENDING'],
            },
        }

        current_secret = _make_secret_value('old-key-id', 'old-key-value')
        pending_secret = _make_secret_value('new-key-id', 'new-key-value')
        sm_client.get_secret_value.side_effect = [
            {'SecretString': current_secret},
            {'SecretString': pending_secret},
        ]

        finish_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        sm_client.update_secret_version_stage.assert_called_once_with(
            SecretId=MOCK_SECRET_ARN,
            VersionStage='AWSCURRENT',
            MoveToVersionId=MOCK_TOKEN,
            RemoveFromVersionId='old-token',
        )

    def test_delete_old_api_key(self, sm_client, ag_client):
        from rotation import finish_secret

        sm_client.describe_secret.return_value = {
            'VersionIdsToStages': {
                'old-token': ['AWSCURRENT'],
                MOCK_TOKEN: ['AWSPENDING'],
            },
        }

        current_secret = _make_secret_value('old-key-id', 'old-key-value')
        pending_secret = _make_secret_value('new-key-id', 'new-key-value')
        sm_client.get_secret_value.side_effect = [
            {'SecretString': current_secret},
            {'SecretString': pending_secret},
        ]

        finish_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        ag_client.delete_usage_plan_key.assert_called_once_with(
            usagePlanId=MOCK_USAGE_PLAN_ID,
            keyId='old-key-id',
        )
        ag_client.delete_api_key.assert_called_once_with(apiKey='old-key-id')

    def test_skip_if_already_current(self, sm_client, ag_client):
        from rotation import finish_secret

        sm_client.describe_secret.return_value = {
            'VersionIdsToStages': {
                MOCK_TOKEN: ['AWSCURRENT'],
            },
        }

        finish_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)

        sm_client.update_secret_version_stage.assert_not_called()
        ag_client.delete_api_key.assert_not_called()


class TestLambdaHandler:
    @pytest.fixture(autouse=True)
    def _patch_boto(self):
        with patch('rotation.boto3') as mock_boto:
            mock_boto.client.side_effect = lambda svc: (
                MagicMock() if svc == 'secretsmanager' else MagicMock()
            )
            self.mock_boto = mock_boto
            yield

    def _make_event(self, step: str) -> dict:
        return {
            'SecretId': MOCK_SECRET_ARN,
            'ClientRequestToken': MOCK_TOKEN,
            'Step': step,
        }

    @patch('rotation.create_secret')
    def test_dispatch_create_secret(self, mock_fn):
        from rotation import lambda_handler
        lambda_handler(self._make_event('createSecret'), None)
        mock_fn.assert_called_once()

    @patch('rotation.set_secret')
    def test_dispatch_set_secret(self, mock_fn):
        from rotation import lambda_handler
        lambda_handler(self._make_event('setSecret'), None)
        mock_fn.assert_called_once()

    @patch('rotation.test_secret')
    def test_dispatch_test_secret(self, mock_fn):
        from rotation import lambda_handler
        lambda_handler(self._make_event('testSecret'), None)
        mock_fn.assert_called_once()

    @patch('rotation.finish_secret')
    def test_dispatch_finish_secret(self, mock_fn):
        from rotation import lambda_handler
        lambda_handler(self._make_event('finishSecret'), None)
        mock_fn.assert_called_once()

    def test_invalid_step(self):
        from rotation import lambda_handler
        with pytest.raises(ValueError, match='Invalid step'):
            lambda_handler(self._make_event('invalidStep'), None)


class TestErrorHandling:
    def test_create_key_failure_propagates(self, sm_client, ag_client):
        from rotation import create_secret

        sm_client.exceptions.ResourceNotFoundException = type('ResourceNotFoundException', (Exception,), {})
        sm_client.get_secret_value.side_effect = [
            sm_client.exceptions.ResourceNotFoundException(),
            {'SecretString': _make_secret_value()},
        ]

        ag_client.create_api_key.side_effect = Exception('API Gateway error')

        with pytest.raises(Exception, match='API Gateway error'):
            create_secret(sm_client, ag_client, MOCK_SECRET_ARN, MOCK_TOKEN)
