import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from free_lunch import content_blocks_dict


class FakeAIMessage:
    def __init__(self, content, model_id="test::model", additional_kwargs=None):
        self.content = content
        self.response_metadata = {"model_id": model_id}
        self.additional_kwargs = additional_kwargs or {}


class FakeToolMessage:
    def __init__(self, content):
        self.content = content


class ContentBlocksDictTest(unittest.TestCase):
    def test_accepts_ai_message(self):
        result = content_blocks_dict(FakeAIMessage("Hello"))

        self.assertEqual(result["text"], "Hello")
        self.assertEqual(result["model_id"], "test::model")

    def test_accepts_agent_response_dict(self):
        raw_response = {
            "messages": [
                FakeAIMessage("", additional_kwargs={"reasoning_content": "Need a tool."}),
                FakeToolMessage("tool output"),
                FakeAIMessage("Final answer", model_id="test::final"),
            ]
        }

        result = content_blocks_dict(raw_response)

        self.assertEqual(result["text"], "Final answer")
        self.assertEqual(result["model_id"], "test::final")

    def test_accepts_message_list(self):
        messages = [
            FakeAIMessage("", additional_kwargs={"reasoning_content": "Need a tool."}),
            FakeToolMessage("tool output"),
            FakeAIMessage("Final answer", model_id="test::final"),
        ]

        result = content_blocks_dict(messages)

        self.assertEqual(result["text"], "Final answer")
        self.assertEqual(result["model_id"], "test::final")

    def test_can_keep_raw_agent_response(self):
        raw_response = {
            "messages": [
                FakeAIMessage("", additional_kwargs={"reasoning_content": "Need a tool."}),
                FakeToolMessage("tool output"),
                FakeAIMessage("Final answer", model_id="test::final"),
            ]
        }

        result = content_blocks_dict(raw_response, include_raw=True)

        self.assertIs(result["raw_response"], raw_response)
        self.assertEqual(result["text"], "Final answer")

    def test_extracts_tagged_reasoning(self):
        result = content_blocks_dict(FakeAIMessage("<think>private</think>Visible"))

        self.assertEqual(result["text"], "Visible")
        self.assertEqual(result["reasoning"], "private")
        self.assertEqual(result["raw_text"], "<think>private</think>Visible")


if __name__ == "__main__":
    unittest.main()
