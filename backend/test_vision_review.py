import unittest
from unittest.mock import patch
from app.llm import evaluate_image
from app.agents.quality_agent import quality_agent_node

class VisionChecks(unittest.TestCase):
    def test_actual_image_path_forwarded(self):
        review = {"score":90,"issues":[],"critical_issues":["Incorrect equipment"]}
        with patch("app.llm.runtime.json", return_value=review) as inference:
            result = evaluate_image("sample.png", {"topic":"care"})
            self.assertEqual(inference.call_args.kwargs["image_path"], "sample.png")
        with patch("app.agents.quality_agent.evaluate_image", return_value=result):
            self.assertFalse(quality_agent_node({"generated_image_path":"sample.png"})["quality_approved"])

    def test_minor_suggestions_pass(self):
        with patch("app.agents.quality_agent.evaluate_image",
                   return_value={"score":85,"issues":["Slight blur"],"critical_issues":[]}):
            self.assertTrue(quality_agent_node({"generated_image_path":"sample.png"})["quality_approved"])

    def test_score_below_threshold(self):
        with patch("app.agents.quality_agent.evaluate_image",
                   return_value={"score":74,"issues":["Unclear"],"critical_issues":[]}):
            self.assertFalse(quality_agent_node({"generated_image_path":"sample.png"})["quality_approved"])

    def test_invalid_review_stops(self):
        with patch("app.llm.runtime.json", return_value={"score":99}):
            with self.assertRaises(ValueError):
                evaluate_image("sample.png", {})

if __name__ == "__main__":
    unittest.main()
