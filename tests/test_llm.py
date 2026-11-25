import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import httpx
import openai
from pydantic import BaseModel

from amigo import config, llm


class Reply(BaseModel):
    text: str


class TestRequest(unittest.TestCase):
    def test_a_refused_request_is_a_model_error_at_once(self):
        sent = httpx.Request("POST", "http://x")
        refused = openai.BadRequestError("bad", response=httpx.Response(400, request=sent), body=None)
        client = mock.Mock()
        client.responses.create.side_effect = refused
        with mock.patch("amigo.llm._client", return_value=client):
            with self.assertRaises(llm.ModelError):
                llm._request([], Reply, "test", "low", "m")
        self.assertEqual(client.responses.create.call_count, 1)

    def test_requests_take_turns_over_the_servers_and_a_retry_goes_to_the_next(self):
        down = openai.APIConnectionError(request=httpx.Request("POST", "http://a"))
        client = mock.Mock()
        client.responses.create.side_effect = [mock.Mock(), down, mock.Mock()]
        with mock.patch("amigo.llm._client", return_value=client) as made, \
                mock.patch("amigo.llm.time.sleep"), \
                mock.patch.dict("amigo.config.LOCAL_MODELS", {"m": "http://a,http://b"}):
            llm._request([], Reply, "test", "low", "m")
            _, attempt, _ = llm._request([], Reply, "test", "low", "m")
        self.assertEqual([c.args[0] for c in made.call_args_list], ["http://a", "http://b", "http://a"])
        self.assertEqual(attempt, 2)

    def test_a_budget_goes_to_chat_completions_and_reads_as_a_response(self):
        usage = mock.Mock(prompt_tokens=10, completion_tokens=30, total_tokens=40,
                          completion_tokens_details=mock.Mock(reasoning_tokens=20))
        choice = mock.Mock(finish_reason="stop", message=mock.Mock(content='{"text": "hi"}'))
        client = mock.Mock()
        client.chat.completions.create.return_value = mock.Mock(id="r", usage=usage, choices=[choice])
        with mock.patch("amigo.llm._client", return_value=client), \
                mock.patch.dict("amigo.config.LOCAL_MODELS", {"m": "http://x"}):
            response, _, _ = llm._request([], Reply, "test", "medium", "m", budget=512)
        sent = client.chat.completions.create.call_args.kwargs
        self.assertEqual(sent["extra_body"], {"thinking_token_budget": 512})
        self.assertEqual(sent["response_format"]["json_schema"]["name"], "Reply")
        self.assertEqual(llm._validate(response, Reply)[0].text, "hi")
        self.assertEqual(llm._usage(response)["reasoning_tokens"], 20)
        client.responses.create.assert_not_called()


@contextmanager
def replying(*texts):
    """llm._request faked: one reply text per request, in order, and nothing logged."""
    replies = iter(texts)
    with mock.patch("amigo.config.CACHE", False), mock.patch("amigo.llm._log_call"), mock.patch(
        "amigo.llm._request", side_effect=lambda *_: (mock.Mock(output_text=next(replies)), 1, 0.0)
    ) as request:
        yield request


class TestCall(unittest.TestCase):
    def test_a_reply_off_the_schema_is_asked_again_once(self):
        with replying('{"txt": "ok"}', '{"text": "ok"}') as request:
            self.assertEqual(llm.call("p", Reply, Path("log"), "test").text, "ok")
        self.assertEqual(request.call_count, 2)
        self.assertIn("did not match the required JSON schema", request.call_args.args[0][-1]["content"])
        with replying("no JSON", '{"txt": "ok"}') as request, self.assertRaises(llm.ModelError):
            llm.call("p", Reply, Path("log"), "test")
        self.assertEqual(request.call_count, 2)


    def test_callers_at_the_same_moment_share_the_first_reply_and_a_refused_one_is_replaced(self):
        replies = iter(["first", "second", "third"])
        with tempfile.TemporaryDirectory() as folder, mock.patch("amigo.config.CACHE", True), \
                mock.patch("amigo.config.CACHE_DIR", Path(folder)), mock.patch("amigo.llm._log_kept"), \
                mock.patch("amigo.llm._call", side_effect=lambda *_: Reply(text=next(replies))):
            self.assertEqual(llm.call("p", Reply, Path("log"), "test").text, "first")
            # a caller that missed the cache just before: its own reply gives way to the one kept
            with mock.patch("amigo.cache.get", return_value=None):
                self.assertEqual(llm.call("p", Reply, Path("log"), "test").text, "first")

            def refuse_first(reply):
                if reply.text == "first":
                    raise llm.ModelError("not this one")

            self.assertEqual(llm.call("p", Reply, Path("log"), "test", check=refuse_first).text, "third")
            self.assertEqual(llm.call("p", Reply, Path("log"), "test").text, "third")
            self.assertEqual(list(Path(folder).rglob("*.part")), [])


class TestCheckLiteral(unittest.TestCase):
    def test_the_fields_must_fit_the_kind(self):
        for fields, ok in (
            ({"kind": "text", "text": "Oslo"}, True),
            ({"kind": "number", "text": "12"}, False),
            ({"kind": "date", "date_end": "2021-12-31"}, True),
            ({"kind": "date", "date_start": "2023-13-01"}, False),
            ({"kind": "date"}, False),
        ):
            entity = llm.Entity(attribute="x", literal=llm.Literal(**fields))
            with self.subTest(fields=fields):
                if ok:
                    llm._check_literal(entity)
                else:
                    with self.assertRaises(llm.ModelError):
                        llm._check_literal(entity)


if __name__ == "__main__":
    unittest.main()


class TestThinking(unittest.TestCase):
    def test_a_level_the_model_lacks_goes_at_the_closest_one_below(self):
        with mock.patch.object(config, "THINKING", None):
            self.assertEqual(llm.thinking("qwen3.8-27b-fp8", "high"), "medium")
            self.assertEqual(llm.thinking("qwen3.8-27b-fp8", "minimal"), "low")
            self.assertEqual(llm.thinking("gpt-6-astra", "none"), "low")
            self.assertEqual(llm.thinking("o3", "high"), "high")  # levels not known: as asked
        with mock.patch.object(config, "THINKING", "none"):
            self.assertEqual(llm.thinking("qwen3.8-27b-fp8", "high"), "none")
