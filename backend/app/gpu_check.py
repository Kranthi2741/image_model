"""Run python -m app.gpu_check before starting the server on the A100."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def main():
    load_dotenv()
    import torch
    from transformers import Qwen3VLForConditionalGeneration, AutoModelForCausalLM
    from diffusers import FluxPipeline
    from app.poster_layout import FONT_NAMES, font_for
    from app.agents.compositor import logo_file, _load_brand
    print('PyTorch:', torch.__version__, 'CUDA runtime:', torch.version.cuda)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable: install the CUDA PyTorch wheel and check nvidia-smi.')
    print('GPU:', torch.cuda.get_device_name(0))
    print('VRAM GiB:', round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1))
    for language in FONT_NAMES:
        font_for(language, '', 24)
        font_for(language, '', 24, True)
        font_for(language, '', 24, True, True)
    logo_file(_load_brand())
    from huggingface_hub import hf_hub_download
    # Small gated config request verifies access without downloading weights.
    hf_hub_download(os.getenv('HF_IMAGE_MODEL', 'black-forest-labs/FLUX.1-dev'),
                    'model_index.json', token=os.getenv('HF_TOKEN') or None)
    print('Preflight passed. Model weights are loaded on the first request.')

if __name__ == '__main__':
    main()
