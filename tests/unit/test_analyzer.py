import json
from unittest.mock import patch, MagicMock
import pytest


class _FakeHTTPResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class TestGetAnalyzerRouting:
    """モデル名前空間によるAnalyzer生成"""

    @patch('analyzer.AnthropicAWS')
    def test_claude_model_returns_claude_analyzer(self, mock_anthropic_cls):
        from analyzer import get_analyzer, ClaudeAnalyzer

        analyzer = get_analyzer('claude-sonnet-5')
        assert isinstance(analyzer, ClaudeAnalyzer)

    @patch('analyzer.AnthropicAWS')
    def test_claude_haiku_model_returns_claude_analyzer(self, mock_anthropic_cls):
        from analyzer import get_analyzer, ClaudeAnalyzer

        analyzer = get_analyzer('claude-haiku-4-5')
        assert isinstance(analyzer, ClaudeAnalyzer)

    def test_bedrock_claude_model_returns_bedrock_claude_analyzer(self):
        from analyzer import get_analyzer, BedrockClaudeAnalyzer

        analyzer = get_analyzer('anthropic.claude-sonnet-5')
        assert isinstance(analyzer, BedrockClaudeAnalyzer)

    def test_bedrock_gpt_model_returns_bedrock_gpt_analyzer(self):
        from analyzer import get_analyzer, BedrockGPTAnalyzer

        analyzer = get_analyzer('openai.gpt-5.5')
        assert isinstance(analyzer, BedrockGPTAnalyzer)

    def test_unsupported_model_raises_value_error(self):
        from analyzer import get_analyzer

        with pytest.raises(ValueError):
            get_analyzer('gpt-4.1-mini')


class TestBedrockClaudeAnalyzer:
    """Bedrock Claude (Mantle / 親クラスのtool_useを再利用)"""

    def _build_response(self, model):
        tool_block = MagicMock()
        tool_block.type = 'tool_use'
        tool_block.input = {
            'found': True,
            'answer': '人物がいます',
            'confidence': 90,
        }
        response = MagicMock()
        response.content = [tool_block]
        response.model = model
        response.usage.input_tokens = 100
        response.usage.output_tokens = 20
        return response

    @patch('analyzer.AnthropicBedrockMantle')
    def test_sonnet_5_uses_default_us_region(self, mock_mantle, monkeypatch):
        monkeypatch.delenv('BEDROCK_US_REGION', raising=False)
        mock_mantle.return_value.messages.create.return_value = (
            self._build_response('anthropic.claude-sonnet-5'))
        from analyzer import BedrockClaudeAnalyzer

        BedrockClaudeAnalyzer().analyze(
            'imagedata', '人物', 'anthropic.claude-sonnet-5')

        mock_mantle.assert_called_once_with(aws_region='us-east-1')

    @patch('analyzer.AnthropicBedrockMantle')
    def test_haiku_uses_default_jp_region(self, mock_mantle, monkeypatch):
        monkeypatch.delenv('BEDROCK_JP_REGION', raising=False)
        mock_mantle.return_value.messages.create.return_value = (
            self._build_response('anthropic.claude-haiku-4-5'))
        from analyzer import BedrockClaudeAnalyzer

        BedrockClaudeAnalyzer().analyze(
            'imagedata', '人物', 'anthropic.claude-haiku-4-5')

        mock_mantle.assert_called_once_with(aws_region='ap-northeast-1')

    @patch('analyzer.AnthropicBedrockMantle')
    def test_region_environment_overrides_are_used(self, mock_mantle, monkeypatch):
        monkeypatch.setenv('BEDROCK_US_REGION', 'us-west-2')
        mock_mantle.return_value.messages.create.return_value = (
            self._build_response('anthropic.claude-sonnet-5'))
        from analyzer import BedrockClaudeAnalyzer

        BedrockClaudeAnalyzer().analyze(
            'imagedata', '人物', 'anthropic.claude-sonnet-5')

        mock_mantle.assert_called_once_with(aws_region='us-west-2')

    @patch('analyzer.AnthropicBedrockMantle')
    def test_clients_are_cached_by_region(self, mock_mantle, mock_env):
        mock_mantle.return_value.messages.create.side_effect = [
            self._build_response('anthropic.claude-haiku-4-5'),
            self._build_response('anthropic.claude-opus-4-8'),
        ]
        from analyzer import BedrockClaudeAnalyzer

        analyzer = BedrockClaudeAnalyzer()
        analyzer.analyze('first', '人物', 'anthropic.claude-haiku-4-5')
        analyzer.analyze('second', '人物', 'anthropic.claude-opus-4-8')

        mock_mantle.assert_called_once_with(aws_region='ap-northeast-1')

    @patch('analyzer.AnthropicBedrockMantle')
    def test_analyze_inherits_forced_tool_use(self, mock_mantle, mock_env):
        mock_mantle.return_value.messages.create.return_value = (
            self._build_response('anthropic.claude-sonnet-5'))
        from analyzer import BedrockClaudeAnalyzer

        result = BedrockClaudeAnalyzer().analyze(
            'imagedata', '人物', 'anthropic.claude-sonnet-5')

        kwargs = mock_mantle.return_value.messages.create.call_args.kwargs
        assert kwargs['tool_choice'] == {
            'type': 'tool', 'name': 'report_analysis'}
        assert kwargs['tools'][0]['name'] == 'report_analysis'
        assert result['found'] is True

    @patch('analyzer.AnthropicBedrockMantle')
    def test_compare_inherits_forced_tool_use(self, mock_mantle, mock_env):
        tool_block = MagicMock()
        tool_block.type = 'tool_use'
        tool_block.input = {
            'danger': False,
            'risk_level': 'none',
            'reason': '危険な変化はありません',
            'changes': '変化はありません',
        }
        response = MagicMock()
        response.content = [tool_block]
        response.model = 'anthropic.claude-haiku-4-5'
        response.usage.input_tokens = 200
        response.usage.output_tokens = 30
        mock_mantle.return_value.messages.create.return_value = response
        from analyzer import BedrockClaudeAnalyzer

        result = BedrockClaudeAnalyzer().compare(
            'before', 'after', '土砂崩れ',
            'anthropic.claude-haiku-4-5')

        kwargs = mock_mantle.return_value.messages.create.call_args.kwargs
        assert kwargs['tool_choice'] == {
            'type': 'tool', 'name': 'report_comparison'}
        assert kwargs['tools'][0]['name'] == 'report_comparison'
        assert result['danger'] is False

    @patch('analyzer.AnthropicBedrockMantle')
    def test_analyze_raises_without_tool_use(self, mock_mantle, mock_env):
        response = MagicMock()
        response.content = [MagicMock(type='text')]
        mock_mantle.return_value.messages.create.return_value = response
        from analyzer import BedrockClaudeAnalyzer

        with pytest.raises(ValueError):
            BedrockClaudeAnalyzer().analyze(
                'imagedata', '人物', 'anthropic.claude-sonnet-5')


class TestBedrockGPTAnalyzer:
    """Bedrock GPT Responses API"""

    def _mock_http(self, monkeypatch, response_body):
        import analyzer as analyzer_module

        mock_urlopen = MagicMock(
            return_value=_FakeHTTPResponse(response_body))
        mock_session = MagicMock()
        mock_session.get_credentials.return_value.get_frozen_credentials.return_value = (
            MagicMock())
        monkeypatch.setattr(analyzer_module, 'urlopen', mock_urlopen)
        monkeypatch.setattr(
            analyzer_module, 'get_session', MagicMock(return_value=mock_session))
        self.mock_sigv4 = MagicMock()
        monkeypatch.setattr(analyzer_module, 'SigV4Auth', self.mock_sigv4)
        return mock_urlopen

    def _analysis_response(self, text=None):
        if text is None:
            text = json.dumps({
                'found': True,
                'answer': '人物がいます',
                'confidence': 92,
            }, ensure_ascii=False)
        return {
            'model': 'openai.gpt-5.5',
            'output': [
                {'type': 'reasoning'},
                {
                    'type': 'message',
                    'content': [
                        {'type': 'output_text', 'text': text},
                    ],
                },
            ],
            'usage': {'input_tokens': 321, 'output_tokens': 45},
        }

    def test_analyze_sends_responses_request_and_parses_output(
            self, monkeypatch, mock_env):
        mock_urlopen = self._mock_http(
            monkeypatch, self._analysis_response())
        from analyzer import BedrockGPTAnalyzer

        result = BedrockGPTAnalyzer().analyze(
            'base64imagedata', '人物', 'openai.gpt-5.5')

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        assert request.full_url == (
            'https://bedrock-mantle.us-east-2.api.aws/openai/v1/responses')
        assert mock_urlopen.call_args.kwargs['timeout'] == 240
        assert self.mock_sigv4.call_args.args[1:] == (
            'bedrock-mantle', 'us-east-2')
        assert payload['store'] is False
        assert payload['max_output_tokens'] == 4000
        assert 'reasoning' not in payload
        content = [
            block
            for message in payload['input']
            for block in message['content']
        ]
        image = next(block for block in content if block['type'] == 'input_image')
        assert image['image_url'] == (
            'data:image/jpeg;base64,base64imagedata')
        assert any(
            block == {
                'type': 'input_text',
                'text': 'この画像に「人物」は存在しますか？',
            }
            for block in content
        )
        text_format = payload['text']['format']
        assert text_format['type'] == 'json_schema'
        assert text_format['name'] == 'report_analysis'
        assert text_format['strict'] is True
        assert text_format['schema']['additionalProperties'] is False
        assert text_format['schema']['required'] == [
            'found', 'answer', 'confidence']
        assert result == {
            'found': True,
            'answer': '人物がいます',
            'confidence': 92,
            'context': 'この画像に「人物」は存在しますか？',
            'model': 'openai.gpt-5.5',
            'usage': {
                'prompt_tokens': 321,
                'completion_tokens': 45,
                'total_tokens': 366,
            },
        }

    def test_effort_adds_reasoning_effort(self, monkeypatch, mock_env):
        mock_urlopen = self._mock_http(
            monkeypatch, self._analysis_response())
        from analyzer import BedrockGPTAnalyzer

        BedrockGPTAnalyzer().analyze(
            'imagedata', '人物', 'openai.gpt-5.5', effort='high')

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        assert payload['reasoning'] == {'effort': 'high'}

    def test_compare_sends_two_images_and_comparison_schema(
            self, monkeypatch, mock_env):
        response = {
            'model': 'openai.gpt-5.4',
            'output': [{
                'type': 'message',
                'content': [{
                    'type': 'output_text',
                    'text': json.dumps({
                        'danger': True,
                        'risk_level': 'high',
                        'reason': '斜面が崩落しています',
                        'changes': '崩落跡が出現しました',
                    }, ensure_ascii=False),
                }],
            }],
            'usage': {'input_tokens': 500, 'output_tokens': 80},
        }
        mock_urlopen = self._mock_http(monkeypatch, response)
        from analyzer import BedrockGPTAnalyzer

        result = BedrockGPTAnalyzer().compare(
            'beforedata', 'iVBORafterdata', '土砂崩れ', 'openai.gpt-5.4')

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        content = [
            block
            for message in payload['input']
            for block in message['content']
        ]
        images = [block for block in content if block['type'] == 'input_image']
        assert images == [
            {'type': 'input_image',
             'image_url': 'data:image/jpeg;base64,beforedata'},
            {'type': 'input_image',
             'image_url': 'data:image/png;base64,iVBORafterdata'},
        ]
        text_format = payload['text']['format']
        assert text_format['name'] == 'report_comparison'
        assert text_format['schema']['properties']['risk_level']['enum'] == [
            'none', 'low', 'medium', 'high']
        assert result['danger'] is True
        assert result['usage'] == {
            'prompt_tokens': 500,
            'completion_tokens': 80,
            'total_tokens': 580,
        }

    def test_missing_output_text_raises_value_error(
            self, monkeypatch, mock_env):
        response = self._analysis_response()
        response['output'][1]['content'] = [{'type': 'refusal'}]
        self._mock_http(monkeypatch, response)
        from analyzer import BedrockGPTAnalyzer

        with pytest.raises(ValueError):
            BedrockGPTAnalyzer().analyze(
                'imagedata', '人物', 'openai.gpt-5.5')

    def test_invalid_output_json_raises_value_error(
            self, monkeypatch, mock_env):
        self._mock_http(
            monkeypatch, self._analysis_response('not valid json'))
        from analyzer import BedrockGPTAnalyzer

        with pytest.raises(ValueError):
            BedrockGPTAnalyzer().analyze(
                'imagedata', '人物', 'openai.gpt-5.5')


class TestClaudeAnalyzer:
    """ClaudeAnalyzer (Claude Platform on AWS / tool_use強制)"""

    def _build_response(self, found=True, answer='人物がいます', confidence=88):
        tool_block = MagicMock()
        tool_block.type = 'tool_use'
        tool_block.name = 'report_analysis'
        tool_block.input = {'found': found, 'answer': answer, 'confidence': confidence}

        response = MagicMock()
        response.content = [tool_block]
        response.model = 'claude-sonnet-5'
        response.usage.input_tokens = 1200
        response.usage.output_tokens = 45
        return response

    @patch('analyzer.AnthropicAWS')
    def test_analyze_returns_expected_format(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        result = ClaudeAnalyzer().analyze('base64data', '人物', 'claude-sonnet-5', 'low')

        assert result['found'] is True
        assert result['answer'] == '人物がいます'
        assert result['confidence'] == 88
        assert result['model'] == 'claude-sonnet-5'
        assert result['context'] == 'この画像に「人物」は存在しますか？'
        assert result['usage'] == {
            'prompt_tokens': 1200,
            'completion_tokens': 45,
            'total_tokens': 1245,
        }

    @patch('analyzer.AnthropicAWS')
    def test_analyze_forces_tool_use_and_sends_image(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().analyze('base64imagedata', '人物', 'claude-sonnet-5', 'low')

        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs['model'] == 'claude-sonnet-5'
        assert kwargs['max_tokens'] == 500
        assert kwargs['tool_choice'] == {'type': 'tool', 'name': 'report_analysis'}
        assert kwargs['tools'][0]['name'] == 'report_analysis'

        content = kwargs['messages'][0]['content']
        image_block = next(b for b in content if b['type'] == 'image')
        assert image_block['source']['type'] == 'base64'
        assert image_block['source']['media_type'] == 'image/jpeg'
        assert image_block['source']['data'] == 'base64imagedata'
        assert any(b['type'] == 'text' for b in content)

    @patch('analyzer.AnthropicAWS')
    def test_analyze_detects_png_media_type(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().analyze('iVBORw0KGgoAAAANSUhEUg', '人物', 'claude-sonnet-5', 'low')

        kwargs = mock_client.messages.create.call_args.kwargs
        image_block = next(b for b in kwargs['messages'][0]['content'] if b['type'] == 'image')
        assert image_block['source']['media_type'] == 'image/png'

    @patch('analyzer.AnthropicAWS')
    def test_analyze_ignores_detail_argument(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        result = ClaudeAnalyzer().analyze('data', '人物', 'claude-sonnet-5', 'high')
        assert result['found'] is True

    @patch('analyzer.AnthropicAWS')
    def test_analyze_passes_effort_output_config(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().analyze('data', '人物', 'claude-sonnet-5', 'low', effort='low')

        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs['output_config'] == {'effort': 'low'}

    @patch('analyzer.AnthropicAWS')
    def test_analyze_omits_output_config_without_effort(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().analyze('data', '人物', 'claude-sonnet-5', 'low')

        kwargs = mock_client.messages.create.call_args.kwargs
        assert 'output_config' not in kwargs

    @patch('analyzer.AnthropicAWS')
    def test_analyze_raises_without_tool_use(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        text_block = MagicMock()
        text_block.type = 'text'
        response = MagicMock()
        response.content = [text_block]
        mock_client.messages.create.return_value = response

        from analyzer import ClaudeAnalyzer

        with pytest.raises(ValueError):
            ClaudeAnalyzer().analyze('data', '人物', 'claude-sonnet-5', 'low')


class TestClaudeOnlyHandler:
    """handler経由のClaude専用挙動"""

    def _claude_result(self):
        return {
            'found': True,
            'answer': '人物がいます',
            'confidence': 80,
            'model': 'claude-sonnet-5',
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            'context': 'この画像に「人物」は存在しますか？',
        }

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('analyzer.AnthropicAWS')
    def test_claude_model_routes_to_claude(self, mock_anthropic, mock_analyze, mock_env):
        mock_analyze.return_value = self._claude_result()
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': json.dumps({
                'image': 'data:image/jpeg;base64,/9j/4AAQ',
                'target': '人物',
                'model': 'claude-sonnet-5',
            }),
            'requestContext': {},
            'resource': '/analyze',
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('analyzer.AnthropicAWS')
    def test_default_model_env_routes_to_claude(self, mock_anthropic, mock_analyze, mock_env, monkeypatch):
        monkeypatch.setenv('DEFAULT_MODEL', 'claude-sonnet-5')
        mock_analyze.return_value = self._claude_result()
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': json.dumps({
                'image': 'data:image/jpeg;base64,/9j/4AAQ',
                'target': '人物',
            }),
            'requestContext': {},
            'resource': '/analyze',
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_analyze.assert_called_once()

    @patch('handler._resolve_analyzer')
    def test_omitted_model_uses_bedrock_sonnet_code_fallback(
            self, mock_resolve, mock_env, monkeypatch):
        monkeypatch.delenv('DEFAULT_MODEL', raising=False)
        analyzer = MagicMock()
        analyzer.analyze.return_value = {
            **self._claude_result(),
            'model': 'anthropic.claude-sonnet-5',
        }
        mock_resolve.return_value = analyzer
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': json.dumps({
                'image': 'data:image/jpeg;base64,/9j/4AAQ',
                'target': '人物',
            }),
            'requestContext': {},
            'resource': '/analyze',
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_resolve.assert_called_once_with('anthropic.claude-sonnet-5')
        assert analyzer.analyze.call_args.args[2] == 'anthropic.claude-sonnet-5'

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('analyzer.AnthropicAWS')
    def test_effort_passed_to_analyzer(self, mock_anthropic, mock_analyze, mock_env):
        mock_analyze.return_value = self._claude_result()
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': json.dumps({
                'image': 'data:image/jpeg;base64,/9j/4AAQ',
                'target': '人物',
                'model': 'claude-sonnet-5',
                'effort': 'low',
            }),
            'requestContext': {},
            'resource': '/analyze',
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert mock_analyze.call_args.kwargs['effort'] == 'low'

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('analyzer.AnthropicAWS')
    def test_omitted_effort_defaults_to_none(self, mock_anthropic, mock_analyze, mock_env):
        mock_analyze.return_value = self._claude_result()
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': json.dumps({
                'image': 'data:image/jpeg;base64,/9j/4AAQ',
                'target': '人物',
                'model': 'claude-sonnet-5',
            }),
            'requestContext': {},
            'resource': '/analyze',
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert mock_analyze.call_args.kwargs['effort'] is None

    def test_invalid_effort_returns_400(self, mock_env):
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': json.dumps({
                'image': 'data:image/jpeg;base64,/9j/4AAQ',
                'target': '人物',
                'model': 'claude-sonnet-5',
                'effort': 'ultra',
            }),
            'requestContext': {},
            'resource': '/analyze',
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'effort' in body['error'].lower()

