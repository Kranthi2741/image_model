"""Local Hugging Face inference interface; imports do not load model weights."""
import json
from app.hf_runtime import runtime

def ask_json(system_prompt, user_prompt, model=None):
    return runtime.json(system_prompt, user_prompt)

def generate_image(prompt, output_path):
    return runtime.image(prompt, output_path)

def evaluate_image(image_path, requirements):
    result = runtime.json(
        "Inspect actual pixels against the requirements. Return JSON with score (integer 0-100), "
        "issues (string array), critical_issues (string array). Check topic alignment, meaningful "
        "storytelling, anatomy, equipment, composition and expected_visible_copy if supplied. "
        "Copy is otherwise added later. Critical defects are wrong topic, misleading medical "
        "meaning, seriously distorted anatomy, or unreadable required text. Stylistic preferences "
        "belong only in issues. Score the actual image; never return a default score.",
        json.dumps(requirements, ensure_ascii=False), image_path=image_path)
    if (type(result.get("score")) is not int or not 0 <= result["score"] <= 100
        or any(not isinstance(result.get(k), list) or
               not all(isinstance(v, str) for v in result[k])
               for k in ("issues", "critical_issues"))):
        raise ValueError("Invalid vision review; no approval issued.")
    return result
