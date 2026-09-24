import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url:
    raise ValueError("SUPABASE_URL missing")

if not key:
    raise ValueError("SUPABASE_SERVICE_KEY missing")

supabase = create_client(url, key)

result = supabase.table("live_status").select("*").execute()

print("Connected to Supabase!")
print(result.data)