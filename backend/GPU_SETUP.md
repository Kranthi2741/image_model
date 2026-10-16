# Hugging Face GPU deployment

Run from this backend directory on a Linux NVIDIA A100 machine. Use one Uvicorn
worker, without reload: every worker would allocate its own model copies.
The web UI can start without a GPU, but model inference requires CUDA.
Hugging Face hosts the weights here; inference runs on your GPU rather than
through a paid Hugging Face provider API. The Qwen models are still LLMs.

## Installation

Use Python 3.10 or 3.11 in a new environment. Keep the existing app_data,
asset_library, assets, uploaded_images and database configuration when copying
the project. Do not copy a Windows virtual environment to Linux.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements-gpu.txt
sudo apt-get update
sudo apt-get install -y fonts-noto-core libraqm0 ffmpeg
```

The CUDA wheel requires a compatible NVIDIA driver; check nvidia-smi first.
If your image supplies a different supported CUDA wheel, install that matching
PyTorch/torchvision pair instead. The pins above are the prepared baseline,
not a claim that this machine has completed GPU verification.

Merge .env.huggingface.example into .env, preserving database and brand settings.
Set HF_TOKEN to a Hugging Face read token and accept access conditions on
https://huggingface.co/black-forest-labs/FLUX.1-dev using the same account.
FLUX.1-dev weights have a non-commercial license: arrange the appropriate
commercial inference license before using this client-marketing deployment
commercially. Output rights and model-use rights are separate; consult the
model license. No KIE, Ollama, OpenRouter or Singularity credentials are used.

Optional: pre-download weights before the first campaign (after setting HF_TOKEN):

```bash
hf download Qwen/Qwen3-8B
hf download Qwen/Qwen3-VL-8B-Instruct
hf download black-forest-labs/FLUX.1-dev
```

```bash
python -m app.gpu_check
python -m unittest discover -s tests -p 'test_hf*.py'
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Bind publicly only behind your normal authenticated network/proxy. Open the app,
confirm the brand logo and database settings, then generate ONE manual campaign
before starting an annual schedule. The first request downloads large weights;
allow ample disk (roughly 120 GB free recommended), host RAM (64 GB or more
recommended), and download time. Model files remain cached for subsequent runs.

## Runtime and image quality

Qwen3-8B plans and writes copy; Qwen3-VL-8B-Instruct reviews real image pixels;
FLUX.1-dev renders artwork at 40 steps by default. HF_IMAGE_STEPS=16 is a
speed experiment, not a guaranteed quality setting. HF_IMAGE_CANDIDATES defaults
to 2 (range 1-4). Candidates vary seeds; the creative director changes composition
on quality retries and considers recent designs. Candidate generation/review is
slower than a single image. Prompt and calendar jobs may both be active, but
GPU operations queue under a shared lock to avoid out-of-memory failures.

Only one model family is retained at once; FLUX uses CPU offload. This supports
both A100 memory variants more conservatively, at the cost of model-switch time.
Start without additional parallel workers. There is no cloud fallback.

Campaign copy is placed in a Qwen-selected rectangle using Noto fonts and RAQM
shaping, preserving native-script text. Original artwork, generation seed/prompt
metadata and candidate posters are saved in generated_images. The selected
finished poster is reviewed before draft storage. Critical defects cannot pass
on score alone. Review is automated assistance, not a guarantee of medical or
language accuracy. Visually inspect a sample in every language you intend to use.

The existing Stop behavior stops further workflow stages after an active model
call returns; it does not interrupt a CUDA kernel. Publishing remains disabled.
No claim is made that an 8B model or FLUX will always match the supplied references.
The A100 smoke run is still required: no GPU/model weights were available during
preparation. If preflight fails, resolve that error before running a batch.

## Model references

- https://huggingface.co/Qwen/Qwen3-8B
- https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct
- https://huggingface.co/black-forest-labs/FLUX.1-dev
- https://huggingface.co/docs/diffusers/api/pipelines/flux
