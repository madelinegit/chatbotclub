import os
from dotenv import load_dotenv

load_dotenv()

# ModelsLab
MODELSLAB_API_KEY   = os.getenv("MODELSLAB_API_KEY")
MODELSLAB_MODEL     = os.getenv("MODELSLAB_MODEL")
MODELSLAB_API_URL   = os.getenv("MODELSLAB_API_URL")
MODELSLAB_IMAGE_URL = os.getenv("MODELSLAB_IMAGE_URL")
MODELSLAB_IMAGE_MODEL = os.getenv("MODELSLAB_IMAGE_MODEL")

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

# Cloudinary (free image hosting for text card uploads)
CLOUDINARY_URL        = os.getenv("CLOUDINARY_URL")
