"""Lazy single-model GPU runtime, shared by calendar and manual workflows."""
import gc
import json
import os
import re
import secrets
import threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def parse_object(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected a complete JSON object")
    return value

class HFRuntime:
    def __init__(self):
        self.lock = threading.RLock()
        self.kind = self.model = self.processor = None

    def _load(self, kind):
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU required for inference. See GPU_SETUP.md.")
        if self.kind == kind:
            return
        self.model = self.processor = self.kind = None
        gc.collect()
        torch.cuda.empty_cache()
        token = os.getenv("HF_TOKEN") or None
        if kind == "image":
            from diffusers import FluxPipeline
            self.model = FluxPipeline.from_pretrained(
                os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev"),
                torch_dtype=torch.bfloat16, token=token)
            self.model.enable_model_cpu_offload()
            self.model.vae.enable_tiling()
        elif kind == "vision":
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
            name = os.getenv("HF_VISION_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
            self.processor = AutoProcessor.from_pretrained(name, token=token)
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                name, torch_dtype=torch.bfloat16, device_map="cuda", token=token,
                attn_implementation="sdpa").eval()
        else:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            name = os.getenv("HF_TEXT_MODEL", "Qwen/Qwen3-8B")
            self.processor = AutoTokenizer.from_pretrained(name, token=token)
            self.model = AutoModelForCausalLM.from_pretrained(
                name, torch_dtype=torch.bfloat16, device_map="cuda", token=token,
                attn_implementation="sdpa").eval()
        self.kind = kind

    def json(self, system, prompt, image_path=None):
        import torch
        with self.lock, torch.inference_mode():
            self._load("vision" if image_path else "text")
            system += "\nReturn only a complete valid JSON object. No markdown."
            for attempt in range(3):
                if image_path:
                    messages = [{"role": "user", "content": [
                        {"type": "image", "image": str(Path(image_path).resolve())},
                        {"type": "text", "text": system + "\n" + prompt}]}]
                    inputs = self.processor.apply_chat_template(messages, tokenize=True,
                        add_generation_prompt=True, return_dict=True, return_tensors="pt").to("cuda")
                else:
                    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
                    text = self.processor.apply_chat_template(messages, tokenize=False,
                        add_generation_prompt=True, enable_thinking=False)
                    inputs = self.processor(text, return_tensors="pt").to("cuda")
                output = self.model.generate(**inputs,
                    max_new_tokens=int(os.getenv("HF_MAX_NEW_TOKENS", "4096")),
                    do_sample=not bool(image_path),
                    **({} if image_path else {"temperature": 0.7, "top_p": 0.8}))
                raw = self.processor.batch_decode(output[:, inputs["input_ids"].shape[1]:],
                                                  skip_special_tokens=True)[0]
                del inputs, output
                try:
                    return parse_object(raw)
                except (ValueError, TypeError):
                    prompt += "\nPrevious response was invalid. Return a concise complete JSON object."
            raise ValueError("Model returned invalid JSON after three attempts; no generic fallback substituted.")

    def image(self, prompt, output_path):
        import torch
        with self.lock, torch.inference_mode():
            self._load("image")
            steps = int(os.getenv("HF_IMAGE_STEPS", "40"))
            if not 1 <= steps <= 100:
                raise ValueError("HF_IMAGE_STEPS must be between 1 and 100")
            width, height = (768, 1344) if "9:16" in prompt else (1344, 768) if "16:9" in prompt else (896, 1120) if "4:5" in prompt else (1024, 1024)
            seed = secrets.randbits(32)
            image = self.model(prompt=prompt, width=width, height=height,
                num_inference_steps=steps, guidance_scale=3.5, max_sequence_length=512,
                generator=torch.Generator("cpu").manual_seed(seed)).images[0]
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, format="PNG")
            destination.with_suffix(".generation.json").write_text(json.dumps({
                "model": os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev"),
                "seed": seed, "steps": steps, "width": width, "height": height,
                "prompt": prompt}, ensure_ascii=False, indent=2), encoding="utf-8")
            return str(destination)

runtime = HFRuntime()
