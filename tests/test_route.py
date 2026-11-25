import unittest
from pathlib import Path
from unittest import mock

from amigo import answer, llm, route, solve

ORIGINAL = "which customer has the credit card that expires first"
SQL = "SELECT customer.id FROM customer ORDER BY customer.card_expiry LIMIT 1"
CONTEXT = "TABLE shop.customer\nname: shop.customer\ncolumns: id, first_name, last_name"

ONE = solve.Interpretation(
    id="i1",
    bindings=[
        solve.Binding(
            entity="e1", column="shop.customer.card_expiry", reason="it fits", value=None
        )
    ],
    tables=["shop.customer"],
)

RESULT = answer.Result(ONE, "the first card to expire", SQL, ["id"], [(7,)], False, None)

TURNS = [
    {
        "question": "Which expiry date do you mean?",
        "options": [{"id": "o1", "label": "the card's own date"}],
        "answer": "o1",
        "typed": None,
    }
]


def fake_call(reply, prompts):
    """Stands in for llm.call: keeps the prompt, runs the check, hands the reply back."""

    def call(prompt, schema, log_path, label, check=None, **rest):
        assert "$" not in prompt
        prompts.append(prompt)
        if check is not None:
            check(reply)
        return reply

    return call


class TestDecide(unittest.TestCase):
    def decide(self, route_word, question, reply="show their names too"):
        self.prompts: list[str] = []
        answered = route.Routed(route=route_word, question=question)
        with mock.patch.object(route.llm, "call", fake_call(answered, self.prompts)), (
            mock.patch.object(route.answer, "context", lambda *args: CONTEXT)
        ):
            return route.decide(None, ORIGINAL, TURNS, RESULT, reply, Path("unused.jsonl"))

    def test_each_route_carries_its_own_code_written_reason(self):
        for word, question in (
            ("rewrite", "which customer has the card that expires first, with their name"),
            ("restart", "which shop sold that customer the most"),
        ):
            with self.subTest(word):
                self.assertEqual(
                    self.decide(word, question),
                    {"route": word, "question": question, "why": route.WHY[word]},
                )

    def test_the_prompt_holds_the_sql_the_columns_and_the_cards(self):
        self.decide("rewrite", "which customer has the card that expires first, with their name")
        prompt = self.prompts[0]
        self.assertIn(SQL, prompt)
        self.assertIn(CONTEXT, prompt)
        self.assertIn("Which expiry date do you mean?", prompt)
        self.assertIn("show their names too", prompt)
        self.assertIn(ORIGINAL, prompt)

    def test_a_route_that_is_neither_word_is_refused(self):
        with self.assertRaises(llm.ModelError) as caught:
            self.decide("answer", "which customer, with their name")
        self.assertIn("answer", str(caught.exception))

    def test_an_empty_question_or_the_original_one_is_refused(self):
        for question in ("   ", ORIGINAL, "  Which CUSTOMER has the credit card   that expires first "):
            with self.assertRaises(llm.ModelError):
                self.decide("rewrite", question)

    def test_a_question_pointing_back_at_the_conversation_is_refused(self):
        with self.assertRaises(llm.ModelError):
            self.decide("rewrite", "the customer identified in list 1, with their name")

    def test_the_banned_pattern_catches_pointers_and_leaves_plain_words_alone(self):
        for question in (
            "list 1",
            "option 2",
            "lists 3",
            "the options above shown above",
            "this conversation",
        ):
            with self.subTest(question):
                self.assertTrue(route.BANNED.findall(question))
        for question in (
            "List the customers and their cards",
            "which cards are worth above 100",
            "what is the option price",
            "which customers are listless",
            "the options that are open",
        ):
            with self.subTest(question):
                self.assertEqual(route.BANNED.findall(question), [])


if __name__ == "__main__":
    unittest.main()
