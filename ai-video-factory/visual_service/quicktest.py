import torch
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,
    safety_checker=None,
)
pipe = pipe.to("cuda")

with torch.autocast("cuda"):
    img = pipe("test prompt", width=512, height=512, num_inference_steps=5).images[0]

print("DONE")
