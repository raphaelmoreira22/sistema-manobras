from supabase import create_client

SUPABASE_URL = "https://pvaxxoresjkerxszsgtk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB2YXh4b3Jlc2prZXJ4c3pzZ3RrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE4NTQxMTUsImV4cCI6MjA5NzQzMDExNX0.G4Tr-HS-brBRO7jOyXGta0xrYqXUtZvXlAmC4PtdfaA"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_manobras():
    return supabase.table("manobras").select("*").execute().data


def add_manobra(dado):
    return supabase.table("manobras").insert(dado).execute()
