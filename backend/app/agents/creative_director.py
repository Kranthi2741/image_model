"""Topic-derived art direction with explicit, dynamically chosen copy placement."""
import json
from pathlib import Path
from app.llm import ask_json

def _recent_designs():
    try:
        records = json.loads((Path(__file__).resolve().parents[2] / "asset_library/index.json").read_text(encoding="utf-8"))
        return [r.get("creative_brief", {}) for r in records[-6:]]
    except (OSError, ValueError, TypeError):
        return []

def creative_director_node(state):
    language = state.get("target_language", "English")
    context = {
        "request": state.get("user_prompt", ""), "plan": state.get("campaign_plan", {}),
        "strategy": state.get("marketing_strategy", {}),
        "previous_direction": state.get("design_direction", {}),
        "language": language, "recent_designs": _recent_designs(),
        "review_feedback": state.get("quality_issues", []),
    }
    system = """You are a campaign art director. Design an original topic-specific visual narrative.
Use cinematic light, believable photographic people, expressive meaningful actions,
rich material detail, clear hierarchy and relevant conceptual illustrations where useful.
Consider three substantially different ideas internally and select the strongest for this request.
Vary focal scale, camera viewpoint, palette, composition and copy placement from recent designs.
No fixed template, obligatory diagonal split, footer, icon row, collage or generic smiling doctor.
A festival-only request must depict the festival without inserting unrelated healthcare.
Use only supplied facts. No invented products, statistics, cures or medical promises.
All visible copy must be concise and in the requested language, with its native script.
Return JSON:
composition (detailed string), topic_visual_direction (string), central_visual (string),
scenes (1-5 objects with action, setting, meaning, placement),
palette (string), lighting (string),
copy_box ([x,y,width,height] normalized 0-1, width>=0.30, height>=0.20, within canvas),
headline (short string), supporting_copy (short string).
Keep all visual descriptions together under 180 words to fit the image encoder.
Cover the requested visual_goals through concrete actions; caption_goals belong in captions.
Return copy_background (hex color or transparent), copy_color (contrasting hex color),
and font_style (sans or serif). Choose typography and backdrop for this visual idea;
do not repeat an identical dark copy card across campaigns.
Choose copy_box based on the visual idea, away from faces or essential actions.
Leave the upper-left 24% width by 13% height clear for the original logo.
The image generator produces artwork without lettering; the application typesets the exact copy."""
    from app.poster_layout import validate_box
    from PIL import ImageColor
    for attempt in range(3):
        brief = ask_json(system, json.dumps(context, ensure_ascii=False))
        try:
            for key in ("composition", "topic_visual_direction", "central_visual", "headline"):
                if not isinstance(brief.get(key), str) or not brief[key].strip():
                    raise ValueError("Missing " + key)
            validate_box(brief.get("copy_box"))
            if brief.get("copy_background", "#10212b") != "transparent":
                ImageColor.getrgb(brief.get("copy_background", "#10212b"))
            ImageColor.getrgb(brief.get("copy_color", "#ffffff"))
            if not isinstance(brief.get("scenes"), list) or not 1 <= len(brief["scenes"]) <= 5:
                raise ValueError("Require 1-5 meaningful scenes")
            for scene in brief["scenes"]:
                if not isinstance(scene, dict) or any(not isinstance(scene.get(k), str) or not scene[k].strip()
                    for k in ("action", "setting", "meaning", "placement")):
                    raise ValueError("Incomplete scene")
            if not isinstance(brief.get("supporting_copy"), str):
                raise ValueError("Missing supporting_copy")
            break
        except (ValueError, TypeError, AttributeError) as error:
            context["schema_feedback"] = str(error)
    else:
        raise ValueError("Creative plan was incomplete after three repairs; no generic template substituted.")
    brief["render_mode"] = "typeset_poster"
    brief["visible_copy"] = {"headline": brief["headline"], "short_copy": brief["supporting_copy"]}
    brief["language"] = language
    ratio = "9:16" if "9:16" in context["request"] else "16:9" if any(
        word in context["request"].lower() for word in ("16:9", "landscape")) else "4:5" if "4:5" in context["request"] else "1:1"
    # Keep the meaningful art direction first, before supporting constraints.
    prompt = (
        f"{brief['central_visual']}. {brief['topic_visual_direction']}. "
        f"Composition: {brief['composition']}. "
        + " ".join(f"{s['placement']}: {s['action']} in {s['setting']}; {s['meaning']}." for s in brief["scenes"])
        + f" Palette: {brief.get('palette', '')}. Lighting: {brief.get('lighting', '')}. "
        "Premium campaign photography with meaningful conceptual detail, realistic anatomy, natural textures, "
        "intentional depth, coherent scale and a clear focal story. "
        f"Quiet negative space in normalized copy rectangle {brief['copy_box']} for later typography. "
        "Keep faces and essential actions outside that rectangle. Upper-left 24% width by 13% height clear for logo. "
        f"No text, letters, numbers, logos, watermarks or fake labels. FORMAT: {ratio}"
    )
    return {"creative_brief": brief, "image_prompt": prompt,
            "selected_concept": {"visual_story": brief["topic_visual_direction"]}}
