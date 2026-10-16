import sys, types, unittest, tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageChops
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.agents.planner import parse_costar
from app.agents import creative_director as cd
from app.agents.compositor import compose, logo_file

class CampaignChecks(unittest.TestCase):
    def test_resource_goal_does_not_require_image_scene(self):
        brief = {"composition":"Connected scenes","topic_visual_direction":"Community care",
                 "central_visual":"Support","avoid":[],"headline":"Care","supporting_copy":"Support","copy_box":[.5,.2,.45,.7],
                 "scenes":[dict(action="Consultation", setting="Office", meaning="Care",
                                placement="left",goal_indices=[0]) for _ in range(3)]}
        state = {"user_prompt":"Awareness and resources for further information",
                 "campaign_plan":{"visual_goals":["Show supportive care"],
                                  "caption_goals":["Offer resources for further information"],
                                  "delivery_requirements":["Instagram"],
                                  "communication_goals":["Show supportive care",
                                                         "Offer resources for further information"]}}
        with patch.object(cd,"ask_json",side_effect=[brief, {"approved":True,"issues":[]}]) as calls:
            result = cd.creative_director_node(state)
            self.assertEqual(calls.call_count, 1)
            self.assertIn("Consultation", result["image_prompt"])

    def test_planner_preserves_goal_groups(self):
        from app.agents import planner
        plan = {"visual_goals":["Show care"],"caption_goals":["Offer resources"],
                "delivery_requirements":["Instagram"],"objective":"Awareness"}
        with patch.object(planner,"ask_json",return_value={"campaign_plan":plan,"costar":{}}):
            result = planner.planner_node({"user_prompt":"Context: Awareness\nObjective: Instagram"})
        self.assertEqual(result["campaign_plan"]["communication_goals"], ["Show care","Offer resources"])
        self.assertEqual(result["campaign_plan"]["delivery_requirements"], ["Instagram"])

    def test_caption_resource_request_is_checked(self):
        from app.agents import content_agent
        state = {"user_prompt":"Offer resources",
                 "campaign_plan":{"caption_goals":["Offer resources"]}}
        with patch.object(content_agent,"ask_json",side_effect=[
                {"caption":"Ask your care team for reliable information.","hashtags":[]},
                {"approved":True,"issues":[]}]) as calls:
            result = content_agent.content_agent_node(state)
        self.assertIn("care team", result["caption"])
        self.assertIn("Offer resources", calls.call_args.args[1])

    def test_costar(self):
        fields = parse_costar("Context: Awareness and access to care\nObjective: Instagram and LinkedIn\nStyle: Brand kit\nTone: Professional\nAudience: Anyone\nResponse: Image")
        self.assertEqual(fields["context"], "Awareness and access to care")
        self.assertEqual(fields["objective"], "Instagram and LinkedIn")
        self.assertEqual(len(fields), 6)

    def test_missing_logo(self):
        with self.assertRaises(ValueError):
            logo_file({"brand_logo_path": "missing-logo.png"})

    def test_render(self):
        for size in [(1080,1080),(1080,1350),(1920,1080)]:
            result = compose(Image.new("RGB",size,"#aabbaa"),
                "Care and Support for Every Family", "Meaningful care begins with understanding", {})
            self.assertEqual(result.size, size)
            inset = max(16, int(size[0] * .035))
            region = result.crop((0, 0, int(size[0]*.25), int(size[1]*.15)))
            self.assertIsNotNone(ImageChops.difference(region, Image.new("RGB", region.size, "#aabbaa")).getbbox())

    def test_invalid_creative_plan_stops(self):
        with patch.object(cd, "ask_json", return_value={}):
            with self.assertRaises(ValueError):
                cd.creative_director_node({"user_prompt":"Care"})

if __name__ == "__main__":
    unittest.main()
