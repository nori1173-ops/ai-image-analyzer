import json
from unittest.mock import patch


def grade_event(api_gateway_event, body_overrides):
    body = json.loads(api_gateway_event['body'])
    body.pop('model', None)
    body.update(body_overrides)
    return {**api_gateway_event, 'body': json.dumps(body, ensure_ascii=False)}


class TestAnalyzeWithGrade:
    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_grade_is_resolved_to_model(self, mock_analyze, api_gateway_event, mock_env, monkeypatch):
        import handler
        monkeypatch.setattr(handler, 'resolve_model', lambda grade: ('claude-sonnet-5', 'mapping'))
        mock_analyze.return_value = {'found': True, 'confidence': 90}

        response = handler.lambda_handler(grade_event(api_gateway_event, {'grade': 'high'}), None)

        assert response['statusCode'] == 200
        assert mock_analyze.call_args.args[2] == 'claude-sonnet-5'

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_explicit_model_wins_over_grade(self, mock_analyze, api_gateway_event, mock_env, monkeypatch):
        import handler
        called = []
        monkeypatch.setattr(handler, 'resolve_model', lambda grade: called.append(grade) or ('claude-sonnet-5', 'mapping'))
        mock_analyze.return_value = {'found': True, 'confidence': 90}

        event = grade_event(api_gateway_event, {'model': 'claude-haiku-4-5', 'grade': 'high'})
        response = handler.lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert mock_analyze.call_args.args[2] == 'claude-haiku-4-5'
        assert called == []

    def test_invalid_grade_returns_400(self, api_gateway_event, mock_env):
        from handler import lambda_handler

        response = lambda_handler(grade_event(api_gateway_event, {'grade': 'premium'}), None)

        assert response['statusCode'] == 400
        assert 'grade' in json.loads(response['body'])['error'].lower()

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_failed_resolution_falls_back_to_default_model(self, mock_analyze, api_gateway_event, mock_env, monkeypatch):
        import handler
        monkeypatch.setattr(handler, 'resolve_model', lambda grade: (None, 'fallback'))
        mock_analyze.return_value = {'found': True, 'confidence': 90}

        response = handler.lambda_handler(grade_event(api_gateway_event, {'grade': 'high'}), None)

        assert response['statusCode'] == 200
        assert mock_analyze.call_args.args[2] == 'claude-haiku-4-5'
