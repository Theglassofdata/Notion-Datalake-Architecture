import requests
import json
import psycopg2
from typing import Optional, Dict, List

# =================================================================
# DATABASE INGESTOR CLASS
# =================================================================

class CitusDataIngestor:
    """
    Handles connecting to the Citus database and ingesting data
    by calling the idempotent upsert functions.
    """
    def __init__(self, db_params: Dict):
        self.conn = psycopg2.connect(**db_params)
        print("✅ Successfully connected to the Citus database.")

    def execute_function(self, function_name: str, params: tuple):
        """
        A generic function to call a stored procedure.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {function_name}({', '.join(['%s'] * len(params))});", params)
                self.conn.commit()
        except Exception as e:
            print(f"❌ Error executing function {function_name}: {e}")
            self.conn.rollback()

    def upsert_profile(self, profile: Dict):
        """Calls the function to upsert a profile."""
        print(f"  -> Upserting profile: {profile.get('email')}")
        self.execute_function('public.handle_profile_upsert', (
            profile.get('id'),
            profile.get('email')
        ))

    def upsert_workspace(self, workspace: Dict):
        """Calls the function to upsert a workspace."""
        print(f"  -> Upserting workspace: {workspace.get('name')}")
        self.execute_function('public.handle_workspace_upsert', (
            workspace.get('id'),
            workspace.get('user_id'),
            workspace.get('name')
        ))

    def upsert_page(self, page: Dict):
        """Calls the function to upsert a page."""
        print(f"  -> Upserting page: {page.get('title')}")
        self.execute_function('public.handle_page_upsert', (
            page.get('id'),
            page.get('workspace_id'),
            page.get('user_id'),
            page.get('title'),
            page.get('content')
        ))

    def close(self):
        self.conn.close()
        print("✅ Database connection closed.")


# =================================================================
# API EXTRACTOR CLASS
# =================================================================

class SupabaseDataExtractor:
    def __init__(self, supabase_url: str, access_token: str):
        self.supabase_url = supabase_url
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'apikey': access_token,
            'Content-Type': 'application/json'
        }
    
    def get_all_data(self, table_name: str) -> List[Dict]:
        """Generic function to get all data from a Supabase table."""
        url = f"{self.supabase_url}/rest/v1/{table_name}?select=*"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            print(f"✅ Extracted {len(data)} rows from '{table_name}'")
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ Error extracting from '{table_name}': {e}")
            return []


# =================================================================
# MAIN EXECUTION
# =================================================================

def main():
    """
    Main function to run the data extraction and ingestion pipeline.
    """
    
    # 🔧 --- CONFIGURATION ---
    SUPABASE_URL = "https://thvbmqrqzetsovrewijb.supabase.co"
    ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRodmJtcXJxemV0c292cmV3aWpiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTkxMzc0NiwiZXhwIjoyMDY3NDg5NzQ2fQ.R0XVCtEIQOIRPLufuEf7_a84wezhy5cJir5qzwGCTpw"

    DB_PARAMS = {
        "host": "localhost",
        "port": "5432",
        "database": "notion_db",
        "user": "postgres",
        "password": "postgres"
    }
    # 🔧 --- END CONFIGURATION ---

    extractor = SupabaseDataExtractor(SUPABASE_URL, ACCESS_TOKEN)
    ingestor = CitusDataIngestor(DB_PARAMS)

    try:
        # --- 1. Extract all data from Supabase tables ---
        print("\n🚀 Starting data extraction from Supabase API...")
        profiles = extractor.get_all_data("profiles")
        workspaces = extractor.get_all_data("workspaces")
        pages = extractor.get_all_data("pages")

        # --- 2. Ingest all data into Citus database ---
        print("\n🚀 Starting data ingestion into Citus database...")
        
        # Ingest profiles
        for profile in profiles:
            ingestor.upsert_profile(profile)

        # Ingest workspaces, associating them with the first available profile
        # if the user_id is missing.
        for workspace in workspaces:
            if not workspace.get('user_id'):
                if profiles:
                    # Assign the first profile's ID to the workspace
                    user_id_to_assign = profiles[0].get('id')
                    workspace['user_id'] = user_id_to_assign
                    print(f"ℹ️ Workspace {workspace.get('id')} is missing a user_id. Assigning user_id: {user_id_to_assign}")
                else:
                    print(f"⚠️ Workspace {workspace.get('id')} is missing a user_id and no profiles were found. Skipping.")
                    continue
            ingestor.upsert_workspace(workspace)

        # Ingest pages
        for page in pages:
            if not page.get('user_id'):
                if profiles:
                    # Assign the first profile's ID to the page
                    user_id_to_assign = profiles[0].get('id')
                    page['user_id'] = user_id_to_assign
                    print(f"ℹ️ Page {page.get('id')} is missing a user_id. Assigning user_id: {user_id_to_assign}")
                else:
                    print(f"⚠️ Page {page.get('id')} is missing a user_id and no profiles were found. Skipping.")
                    continue
            ingestor.upsert_page(page)

        print("\n✅ Data ingestion completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred during the pipeline: {e}")
    finally:
        ingestor.close()


if __name__ == "__main__":
    main()
