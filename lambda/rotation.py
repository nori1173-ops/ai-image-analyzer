import json
import boto3


def create_secret(sm_client, ag_client, secret_arn: str, token: str) -> None:
    try:
        sm_client.get_secret_value(
            SecretId=secret_arn,
            VersionId=token,
            VersionStage='AWSPENDING',
        )
        return
    except sm_client.exceptions.ResourceNotFoundException:
        pass

    current = json.loads(
        sm_client.get_secret_value(
            SecretId=secret_arn,
            VersionStage='AWSCURRENT',
        )['SecretString']
    )

    new_key = ag_client.create_api_key(
        name=f"{current['resourcePrefix']}-rotated-key",
        enabled=True,
        stageKeys=[{
            'restApiId': current['restApiId'],
            'stageName': current['stageName'],
        }],
    )

    new_secret = {
        **current,
        'apiKeyId': new_key['id'],
        'apiKeyValue': new_key['value'],
    }

    sm_client.put_secret_value(
        SecretId=secret_arn,
        ClientRequestToken=token,
        SecretString=json.dumps(new_secret),
        VersionStages=['AWSPENDING'],
    )


def set_secret(sm_client, ag_client, secret_arn: str, token: str) -> None:
    pending = json.loads(
        sm_client.get_secret_value(
            SecretId=secret_arn,
            VersionId=token,
            VersionStage='AWSPENDING',
        )['SecretString']
    )

    ag_client.create_usage_plan_key(
        usagePlanId=pending['usagePlanId'],
        keyId=pending['apiKeyId'],
        keyType='API_KEY',
    )


def test_secret(sm_client, ag_client, secret_arn: str, token: str) -> None:
    pending = json.loads(
        sm_client.get_secret_value(
            SecretId=secret_arn,
            VersionId=token,
            VersionStage='AWSPENDING',
        )['SecretString']
    )

    key_info = ag_client.get_api_key(apiKey=pending['apiKeyId'], includeValue=False)
    if not key_info.get('enabled'):
        raise ValueError(f"API key {pending['apiKeyId']} is not enabled")


def finish_secret(sm_client, ag_client, secret_arn: str, token: str) -> None:
    metadata = sm_client.describe_secret(SecretId=secret_arn)
    versions = metadata.get('VersionIdsToStages', {})

    if versions.get(token) == ['AWSCURRENT']:
        return

    current_version = None
    for vid, stages in versions.items():
        if 'AWSCURRENT' in stages and vid != token:
            current_version = vid
            break

    if current_version is None:
        return

    current_secret = json.loads(
        sm_client.get_secret_value(
            SecretId=secret_arn,
            VersionId=current_version,
            VersionStage='AWSCURRENT',
        )['SecretString']
    )

    sm_client.update_secret_version_stage(
        SecretId=secret_arn,
        VersionStage='AWSCURRENT',
        MoveToVersionId=token,
        RemoveFromVersionId=current_version,
    )

    old_key_id = current_secret['apiKeyId']
    ag_client.delete_usage_plan_key(
        usagePlanId=current_secret['usagePlanId'],
        keyId=old_key_id,
    )
    ag_client.delete_api_key(apiKey=old_key_id)


def lambda_handler(event, context):
    secret_arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    sm_client = boto3.client('secretsmanager')
    ag_client = boto3.client('apigateway')

    steps = {
        'createSecret': create_secret,
        'setSecret': set_secret,
        'testSecret': test_secret,
        'finishSecret': finish_secret,
    }

    if step not in steps:
        raise ValueError(f"Invalid step: {step}")

    steps[step](sm_client, ag_client, secret_arn, token)
