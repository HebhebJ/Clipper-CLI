import torch
from diffusers import AutoPipelineForText2Image
from PIL import Image, ImageTk
import tkinter as tk
from pathlib import Path

# -------------------------------
# Global config
# -------------------------------

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("[sd] Using device:", DEVICE)

torch.set_grad_enabled(False)

# -------------------------------
# Load SDXL TURBO
# -------------------------------

pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sdxl-turbo",
    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
    variant="fp16",
    use_safetensors=True,
)

if DEVICE == "cuda":
    pipe.to("cuda")
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    pipe.enable_vae_tiling()

pipe.set_progress_bar_config(disable=True)

# -------------------------------
# Save directory
# -------------------------------

SAVE_DIR = Path("generated_images")
SAVE_DIR.mkdir(exist_ok=True)

# -------------------------------
# Generate → Save → Display
# -------------------------------

def generate():
    prompt = prompt_entry.get("1.0", "end").strip()
    if not prompt:
        status_text.set("Enter a prompt first!")
        return

    status_text.set("Generating...")
    root.update_idletasks()

    safe_name = prompt[:40].replace(" ", "_").replace("/", "_")
    save_path = SAVE_DIR / f"{safe_name}.png"

    width, height = 512, 768  # vertical-ish but lighter than 576x1024

    try:
        # SDXL Turbo is trained for low steps & no CFG
        img = pipe(
            prompt,
            width=width,
            height=height,
            num_inference_steps=1,   # 1 step is the intended use
            guidance_scale=0.0,      # recommended for Turbo
        ).images[0]
    except RuntimeError as e:
        status_text.set(f"Error: {e}")
        return

    img.save(save_path)

    # Preview smaller
    preview = img.resize((350, 525), Image.LANCZOS)
    tk_img = ImageTk.PhotoImage(preview)

    img_label.config(image=tk_img)
    img_label.image = tk_img

    status_text.set(f"Saved: {save_path}")

# -------------------------------
# GUI
# -------------------------------

root = tk.Tk()
root.title("SDXL TURBO GUI - RTX 4050")
root.geometry("700x900")

tk.Label(root, text="Prompt:", font=("Arial", 14)).pack()
prompt_entry = tk.Text(root, height=4, width=70, font=("Arial", 11))
prompt_entry.pack()

status_text = tk.StringVar()
status_label = tk.Label(root, textvariable=status_text, font=("Arial", 12), fg="blue")
status_label.pack(pady=5)

generate_btn = tk.Button(root, text="Generate", font=("Arial", 14), command=generate)
generate_btn.pack(pady=10)

img_label = tk.Label(root)
img_label.pack()

root.mainloop()
