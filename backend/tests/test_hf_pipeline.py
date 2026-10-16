"""CPU-only migration regression tests; no model weights or network calls."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from app.hf_runtime import parse_object
from app.llm import evaluate_image
from app.poster_layout import validate_box
from app.agents.quality_agent import quality_agent_node, route_after_quality
from app.agents.creative_director import creative_director_node
from app.agents.image_generator import image_generator_node

class HFTests(unittest.TestCase):
    def test_json_rejects_truncation_and_non_object(self):
        self.assertEqual(parse_object('```json\n{"ok":true}\n```'), {"ok": True})
        for raw in ('{"ok":', '[]', 'Here is {"ok":true}'):
            with self.assertRaises(ValueError):
                parse_object(raw)

    def test_invalid_vision_response_never_approved(self):
        with patch("app.llm.runtime.json", return_value={"score": 99}):
            with self.assertRaises(ValueError):
                evaluate_image("unused", {})
    
    def test_critical_issue_blocks_high_score(self):
        result = {"score": 98, "issues": [], "critical_issues": ["Wrong subject"]}
        with patch("app.agents.quality_agent.evaluate_image", return_value=result):
            state = quality_agent_node({"generated_image_path": "unused"})
        self.assertFalse(state["quality_approved"])
        self.assertEqual(route_after_quality(state), "creative_director")

    def test_box_must_fit_and_avoid_logo(self):
        self.assertEqual(validate_box([.5,.2,.45,.7]), [.5,.2,.45,.7])
        for box in ([0,0,.5,.5], [.8,.2,.5,.5], [float("nan"),.2,.5,.5], [0,.5,.1,.3]):
            with self.assertRaises(ValueError):
                validate_box(box)

    def test_creative_plan_preserves_language_and_dynamic_placement(self):
        brief = {"composition": "foreground care interaction", "topic_visual_direction": "care",
                 "central_visual": "caregiver helps patient", "headline": "स्वास्थ्य",
                 "supporting_copy": "", "copy_box": [.5,.2,.45,.7],
                 "scenes": [{"action":"help", "setting":"home", "meaning":"support", "placement":"left"}]}
        with patch("app.agents.creative_director.ask_json", return_value=brief):
            state = creative_director_node({"user_prompt":"care", "target_language":"Hindi"})
        self.assertEqual(state["creative_brief"]["visible_copy"]["headline"], "स्वास्थ्य")
        self.assertIn("[0.5, 0.2, 0.45, 0.7]", state["image_prompt"])
        self.assertEqual(state["creative_brief"]["render_mode"], "typeset_poster")

    def test_candidates_rank_no_critical_above_higher_score(self):
        from app.agents import image_generator as module
        with tempfile.TemporaryDirectory() as directory:
            def generate(prompt, path):
                Image.new("RGB", (64,64)).save(path)
                return path
            with patch.object(module, "OUTPUT_DIR", directory), \
                 patch.object(module, "generate_image", side_effect=generate), \
                 patch("app.agents.compositor.logo_file", return_value=Path(directory)/"logo.png"), \
                 patch("app.agents.compositor._load_brand", return_value={}), \
                 patch("app.llm.evaluate_image", side_effect=[
                     {"score":99,"issues":[],"critical_issues":["Wrong anatomy"]},
                     {"score":82,"issues":[],"critical_issues":[]}]), \
                 patch.dict("os.environ", {"HF_IMAGE_CANDIDATES":"2"}):
                result = image_generator_node({"image_prompt":"care", "creative_brief":{}})
            self.assertEqual(result["candidate_review"]["score"], 82)
            self.assertIn("_v2", result["generated_image_path"])

if __name__ == "__main__":
    unittest.main()
