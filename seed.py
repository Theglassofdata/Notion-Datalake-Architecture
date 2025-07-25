import requests
import uuid
import random
from faker import Faker
from datetime import datetime

# === 🔐 Supabase Configuration ===
SUPABASE_URL = "https://thvbmqrqzetsovrewijb.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRodmJtcXJxemV0c292cmV3aWpiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTkxMzc0NiwiZXhwIjoyMDY3NDg5NzQ2fQ.R0XVCtEIQOIRPLufuEf7_a84wezhy5cJir5qzwGCTpw"  # replace with real key
SUPABASE_ANON_KEY = "YOUR_ANON_KEY"  # optional for client-side calls

HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

faker = Faker()

def clear_table(table):
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=not.is.null"
    response = requests.delete(url, headers=HEADERS)
    if response.status_code == 204:
        print(f"  -> Cleared '{table}'")
    else:
        print(f"  ❌ Failed to clear '{table}': {response.text}")

def create_user(email, password):
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()

def get_profiles():
    url = f"{SUPABASE_URL}/rest/v1/profiles"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def insert_workspaces(workspaces):
    url = f"{SUPABASE_URL}/rest/v1/workspaces"
    response = requests.post(url, headers=HEADERS, json=workspaces)
    if response.status_code in [200, 201]:
        print(f"✅ Inserted {len(workspaces)} into 'workspaces'")
    else:
        print(f"❌ Error inserting into 'workspaces': {response.text}")
        print("🔄 Retrying workspaces individually...")
        for i, ws in enumerate(workspaces, 1):
            r = requests.post(url, headers=HEADERS, json=[ws])
            if r.status_code in [200, 201]:
                print(f"  -> Workspace {i} inserted")
            else:
                print(f"  ❌ Workspace {i} failed: {r.text}")

if __name__ == "__main__":
    print("✅ Seeder initialized.\n")

    # === 🔥 Clear existing data ===
    print("🔥 Clearing existing data...")
    for table in ["page_collaborators", "pages", "workspace_members", "workspaces", "profiles"]:
        clear_table(table)

    print("\n🚀 Seeding 25 users and associated data...")
    users = []
    for _ in range(25):
        email = faker.email()
        password = "Password123!"
        try:
            user = create_user(email, password)
            print(f"  ✅ Created user: {email}")
            users.append({
                "id": user["id"],
                "email": email,
                "full_name": faker.name(),
                "avatar_url": faker.image_url()
            })
        except Exception as e:
            print(f"  ❌ Failed to create user {email}: {e}")

    print("\n📥 Skipping manual profile inserts (handled by Supabase trigger)...")
    try:
        profiles = get_profiles()
        print(f"✅ Loaded {len(profiles)} profiles from database")
    except Exception as e:
        print(f"❌ Could not load profiles: {e}")
        exit(1)

    # === 🧩 Insert workspaces ===
    workspaces = []
    for profile in profiles:
        workspaces.append({
            "id": str(uuid.uuid4()),
            "name": "Personal Workspace",
            "owner_id": profile["id"],
            "icon": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })

    insert_workspaces(workspaces)
