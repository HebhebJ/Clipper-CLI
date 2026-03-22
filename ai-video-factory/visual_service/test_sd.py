from pathlib import Path
import torch
from diffusers import StableDiffusionPipeline

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", DEVICE)

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    safety_checker=None,
)
pipe = pipe.to(DEVICE)

prompt = "Saudi arabia dunes and petroleum pumps, cinematic lighting, ultra detailed, 4k, concept art, vertical composition"
with torch.autocast("cuda") if DEVICE == "cuda" else torch.no_grad():
    img = pipe(prompt, width=576, height=1024, num_inference_steps=20).images[0]

out = Path("SA_sc.png")
img.save(out)
print("Saved:", out.resolve())
