import os
from dotenv import load_dotenv

load_dotenv()

# ModelsLab
MODELSLAB_API_KEY   = os.getenv("MODELSLAB_API_KEY")
MODELSLAB_MODEL     = os.getenv("MODELSLAB_MODEL")
MODELSLAB_API_URL   = os.getenv("MODELSLAB_API_URL")
MODELSLAB_IMAGE_URL = os.getenv("MODELSLAB_IMAGE_URL")
MODELSLAB_IMAGE_MODEL = os.getenv("MODELSLAB_IMAGE_MODEL")
# Per-use-case models — fall back to MODELSLAB_IMAGE_MODEL if not set
MODELSLAB_PORTRAIT_MODEL  = os.getenv("MODELSLAB_PORTRAIT_MODEL",  os.getenv("MODELSLAB_IMAGE_MODEL"))
MODELSLAB_SCENE_MODEL     = os.getenv("MODELSLAB_SCENE_MODEL",     os.getenv("MODELSLAB_IMAGE_MODEL"))
MODELSLAB_EXPLICIT_MODEL  = os.getenv("MODELSLAB_EXPLICIT_MODEL",  os.getenv("MODELSLAB_IMAGE_MODEL"))
MODELSLAB_LORA_MODEL      = os.getenv("MODELSLAB_LORA_MODEL")   # HuggingFace repo "user/repo" for trained LoRA
MODELSLAB_FLUX_BASE       = os.getenv("MODELSLAB_FLUX_BASE", "flux")  # Flux base model for LoRA inference

# Replicate — Flux LoRA inference
REPLICATE_API_TOKEN              = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_LORA_VERSION_MAYA      = os.getenv("REPLICATE_LORA_VERSION_MAYA")
REPLICATE_LORA_VERSION_MAYALEJA  = os.getenv("REPLICATE_LORA_VERSION_MAYALEJA")
REPLICATE_TRIGGER_WORD_MAYA      = os.getenv("REPLICATE_TRIGGER_WORD_MAYA", "mayaselfie")
REPLICATE_TRIGGER_WORD_MAYALEJA  = os.getenv("REPLICATE_TRIGGER_WORD_MAYALEJA", "mayaleja")
# Legacy fallback
REPLICATE_LORA_VERSION           = os.getenv("REPLICATE_LORA_VERSION")
REPLICATE_TRIGGER_WORD           = os.getenv("REPLICATE_TRIGGER_WORD", "mayaleja")

# Supabase
SUPABASE_URL        = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY   = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# CCBill (placeholder until approved)
CCBILL_ACCOUNT_NUM  = os.getenv("CCBILL_ACCOUNT_NUM")
CCBILL_SUBACCOUNT   = os.getenv("CCBILL_SUBACCOUNT")
CCBILL_SECRET_KEY   = os.getenv("CCBILL_SECRET_KEY")

# App
DATABASE_URL        = os.getenv("DATABASE_URL")
OWNER_EMAIL         = os.getenv("OWNER_EMAIL")
PERSONA_FILE        = os.getenv("PERSONA_FILE", "persona/maya.txt")
SECRET_KEY          = os.getenv("SECRET_KEY", "change-me-in-production")

# Set to "true" in development to bypass credit checks
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# X (Twitter)
X_API_KEY             = os.getenv("X_API_KEY")
X_API_SECRET          = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN        = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Social
POSTS_PER_DAY = int(os.getenv("POSTS_PER_DAY", "4"))

# Threads
THREADS_ACCESS_TOKEN  = os.getenv("THREADS_ACCESS_TOKEN")

# Instagram (separate Facebook User Access Token with instagram_content_publish scope)
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
# Optional: set this directly to skip the /me/accounts lookup (get it from ig-debug or Graph API Explorer)
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID")

# Cloudinary (free image hosting for text card uploads)
CLOUDINARY_URL        = os.getenv("CLOUDINARY_URL")

# Anthropic (Haiku for caption/text post generation)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Email notifications (Gmail SMTP)
NOTIFY_EMAIL      = os.getenv("NOTIFY_EMAIL", "ecodevwy@gmail.com")
GMAIL_USER        = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
