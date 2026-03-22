import torch
from diffusers import StableDiffusionXLPipeline
from PIL import Image, ImageTk
import tkinter as tk
from pathlib import Path

# -------------------------------
# Device / dtype
# -------------------------------

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("[sd] Using device:", DEVICE)

torch.set_grad_enabled(False)

if DEVICE == "cuda" and torch.cuda.is_bf16_supported():
    DTYPE = torch.bfloat16
    print("[sd] Using bfloat16 on CUDA")
elif DEVICE == "cuda":
    DTYPE = torch.float16
    print("[sd] Using float16 on CUDA")
else:
    DTYPE = torch.float32
    print("[sd] Using float32 on CPU")

# -------------------------------
# Load SDXL BASE 1.0 (quality mode)
# -------------------------------

pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=DTYPE,
    variant="fp16",
    use_safetensors=True,
)

if DEVICE == "cuda":
    # let accelerate handle offloading between CPU/GPU
    pipe.enable_model_cpu_offload()
else:
    pipe.to("cpu")

pipe.set_progress_bar_config(disable=False)

# -------------------------------
# Save directory
# -------------------------------

SAVE_DIR = Path("generated_images")
SAVE_DIR.mkdir(exist_ok=True)

DEFAULT_NEG = (
    "blurry, low quality, distorted, deformed, extra limbs, mutated, "
    "ugly, noisy, grainy, watermark, text, logo, disfigured, bad anatomy, "
    "cropped, out of frame, duplicate, glitch, abstract"
)

# -------------------------------
# Generate → Save → Display
# -------------------------------

def generate():
    prompt = prompt_entry.get("1.0", "end").strip()
    neg = neg_entry.get("1.0", "end").strip()

    if not prompt:
        status_text.set("Enter a prompt first!")
        return

    if not neg:
        neg = DEFAULT_NEG

    status_text.set("Generating (this can take ~20s)...")
    root.update_idletasks()

    safe_name = prompt[:40].replace(" ", "_").replace("/", "_")
    save_path = SAVE_DIR / f"{safe_name}.png"

    # SDXL quality settings
    width, height = 768, 1152    # vertical, decent size
    steps = 20
    guidance = 6.5

    try:
        with torch.no_grad():
            result = pipe(
                prompt=prompt,
                negative_prompt=neg,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance,
            )
            img = result.images[0]
    except RuntimeError as e:
        status_text.set(f"Runtime error: {e}")
        return

    img.save(save_path)

    # preview smaller in GUI
    preview = img.resize((350, 525), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(preview)

    img_label.config(image=tk_img)
    img_label.image = tk_img

    status_text.set(f"Saved: {save_path}")

# -------------------------------
# GUI
# -------------------------------

root = tk.Tk()
root.title("SDXL Base GUI - Quality Mode")
root.geometry("720x950")

tk.Label(root, text="Prompt:", font=("Arial", 14)).pack()
prompt_entry = tk.Text(root, height=4, width=70, font=("Arial", 11))
prompt_entry.pack()

tk.Label(root, text="Negative prompt (optional):", font=("Arial", 12)).pack()
neg_entry = tk.Text(root, height=3, width=70, font=("Arial", 10))
neg_entry.insert("1.0", DEFAULT_NEG)
neg_entry.pack()

status_text = tk.StringVar()
status_label = tk.Label(root, textvariable=status_text, font=("Arial", 12), fg="blue")
status_label.pack(pady=5)

generate_btn = tk.Button(root, text="Generate (slow but good)", font=("Arial", 14), command=generate)
generate_btn.pack(pady=10)

img_label = tk.Label(root)
img_label.pack()

root.mainloop()
