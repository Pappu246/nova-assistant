"""
Groq 400 JSON fix tests (Problem 4) - rt_brain.py
openai/gpt-oss-120b pe 'Error 400: Failed to generate JSON' aaye to
bina response_format ke retry hona chahiye.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rt_brain


class _FakeResp:
    def __init__(self, content):
        msg = type("M", (), {"content": content})()
        self.choices = [type("C", (), {"message": msg})()]


class _FakeClient:
    """Pehla json_object call 400 deta hai, bina response_format wala chalta hai."""

    def __init__(self, json_error=True, content='{"mode": "chat", "reply": "hello Boss"}'):
        self.calls = []
        self.json_error = json_error
        self.content = content
        outer = self

        class _Completions:
            def create(self, **kw):
                outer.calls.append(kw)
                if "response_format" in kw and outer.json_error:
                    raise Exception(
                        "Error code: 400 - {'error': {'message': 'Failed to generate JSON. "
                        "Please adjust your prompt.', 'type': 'invalid_request_error'}}"
                    )
                return _FakeResp(outer.content)

        self.chat = type("Chat", (), {"completions": _Completions()})()


def test_retries_without_response_format_on_400_json_error():
    client = _FakeClient(json_error=True)
    resp = rt_brain._chat_completion_with_json_fallback(
        client, "openai/gpt-oss-120b", [{"role": "user", "content": "hi"}])
    assert len(client.calls) == 2
    assert "response_format" in client.calls[0]
    assert "response_format" not in client.calls[1]
    assert resp.choices[0].message.content.startswith('{"mode"')


def test_no_retry_when_json_mode_works():
    client = _FakeClient(json_error=False)
    resp = rt_brain._chat_completion_with_json_fallback(
        client, "openai/gpt-oss-120b", [{"role": "user", "content": "hi"}])
    assert len(client.calls) == 1
    assert "response_format" in client.calls[0]
    assert resp is not None


def test_unrelated_errors_still_raise():
    class _BoomClient(_FakeClient):
        def __init__(self):
            super().__init__()
            outer = self

            class _Completions:
                def create(self, **kw):
                    outer.calls.append(kw)
                    raise Exception("Connection timed out")

            self.chat = type("Chat", (), {"completions": _Completions()})()

    client = _BoomClient()
    with pytest.raises(Exception, match="timed out"):
        rt_brain._chat_completion_with_json_fallback(
            client, "openai/gpt-oss-120b", [{"role": "user", "content": "hi"}])
    assert len(client.calls) == 1  # retry sirf json/400 errors pe
