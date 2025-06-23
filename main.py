import faker
import psycopg2
import random
import uuid
import json
from datetime import datetime

fake = faker.Faker()


def generate_workspace():
    return {
        "workspace_id": str(uuid.uuid4()),
        "name": fake.company() + " Workspace",
        "created_at": fake.date_time_between(start_date='-2y', end_date='now')
    }

def generate_user_account(workspace_id):
    return {
        "user_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "email": fake.email(),
        "name": fake.name(),
        "created_at": fake.date_time_between(start_date='-1y', end_date='now')
    }

def generate_page(workspace_id, created_by_user_id, created_by_workspace_id):
    return {
        "page_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "title": fake.catch_phrase(),
        "created_by": created_by_user_id,
        "created_by_workspace": created_by_workspace_id,
        "created_at": fake.date_time_between(start_date='-6m', end_date='now')
    }

def generate_block(workspace_id, page_id, created_by_user_id, created_by_workspace_id, parent_block_id=None):
    block_types = ['paragraph', 'heading', 'image', 'table', 'list', 'code']
    block_type = random.choice(block_types)

    content = {}
    if block_type == 'paragraph':
        content = {"text": fake.paragraph()}
    elif block_type == 'heading':
        content = {"text": fake.sentence(), "level": random.randint(1, 3)}
    elif block_type == 'image':
        content = {"url": fake.image_url(), "caption": fake.sentence()}
    elif block_type == 'table':
        content = {"rows": 3, "columns": 4}
    elif block_type == 'list':
        content = {"items": [fake.word() for _ in range(3)], "type": random.choice(["bullet", "numbered"])}
    elif block_type == 'code':
        content = {"language": "python", "code": "print('Hello World')"}

    return {
        "block_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "page_id": page_id,
        "parent_block_id": parent_block_id,
        "block_type": block_type,
        "content": content,
        "created_by": created_by_user_id,
        "created_by_workspace": created_by_workspace_id,
        "created_at": fake.date_time_between(start_date='-3m', end_date='now')
    }

def generate_comment(workspace_id, block_id, user_id, user_workspace_id):
    return {
        "comment_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "block_id": block_id,
        "user_id": user_id,
        "user_workspace_id": user_workspace_id,
        "content": fake.sentence(),
        "created_at": fake.date_time_between(start_date='-2m', end_date='now')
    }

def generate_page_share(workspace_id, page_id, shared_with_user_id, shared_with_workspace_id):
    return {
        "share_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "page_id": page_id,
        "shared_with": shared_with_user_id,
        "shared_with_workspace": shared_with_workspace_id,
        "permission": random.choice(['read', 'edit', 'comment']),
        "created_at": fake.date_time_between(start_date='-1m', end_date='now')
    }

def generate_tag(workspace_id):
    tag_name = fake.word().lower()
    return {
        "tag_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "name": tag_name,
        "created_at": fake.date_time_between(start_date='-1y', end_date='now')
    }

def generate_page_tag(workspace_id, page_id, tag_id):
    return {
        "workspace_id": workspace_id,
        "page_id": page_id,
        "tag_id": tag_id
    }

def insert_single_dataset(conn):
    cursor = conn.cursor()

    try:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Inserting single dataset...")

        # 1. Workspace
        workspace = generate_workspace()
        cursor.execute("""
            INSERT INTO notion.workspace (workspace_id, name, created_at)
            VALUES (%s, %s, %s)
        """, (workspace["workspace_id"], workspace["name"], workspace["created_at"]))
        print("  ✓ Workspace inserted")

        # 2. Users
        users = []
        for _ in range(2):
            user = generate_user_account(workspace["workspace_id"])
            users.append(user)
            cursor.execute("""
                INSERT INTO notion.user_account (user_id, workspace_id, email, name, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user["user_id"], user["workspace_id"], user["email"], user["name"], user["created_at"]))
        print("  ✓ 2 Users inserted")

        # 3. Tags
        tags = []
        for _ in range(2):
            tag = generate_tag(workspace["workspace_id"])
            tags.append(tag)
            cursor.execute("""
                INSERT INTO notion.tag (tag_id, workspace_id, name, created_at)
                VALUES (%s, %s, %s, %s)
            """, (tag["tag_id"], tag["workspace_id"], tag["name"], tag["created_at"]))
        print("  ✓ 2 Tags inserted")

        # 4. Page
        creator = users[0]
        page = generate_page(workspace["workspace_id"], creator["user_id"], creator["workspace_id"])
        cursor.execute("""
            INSERT INTO notion.page (page_id, workspace_id, title, created_by, created_by_workspace, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (page["page_id"], page["workspace_id"], page["title"], page["created_by"], page["created_by_workspace"], page["created_at"]))
        print("  ✓ Page inserted")

        # 5. Blocks
        blocks = []
        for _ in range(2):
            block = generate_block(workspace["workspace_id"], page["page_id"], creator["user_id"], creator["workspace_id"])
            blocks.append(block)
            cursor.execute("""
                INSERT INTO notion.block (block_id, workspace_id, page_id, parent_block_id, block_type, content, created_by, created_by_workspace, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (block["block_id"], block["workspace_id"], block["page_id"], block["parent_block_id"], block["block_type"],
                  json.dumps(block["content"]), block["created_by"], block["created_by_workspace"], block["created_at"]))
        print("  ✓ 2 Blocks inserted")

        # 6. Comment
        comment = generate_comment(workspace["workspace_id"], blocks[0]["block_id"], users[1]["user_id"], users[1]["workspace_id"])
        cursor.execute("""
            INSERT INTO notion.comment (comment_id, workspace_id, block_id, user_id, user_workspace_id, content, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (comment["comment_id"], comment["workspace_id"], comment["block_id"], comment["user_id"],
              comment["user_workspace_id"], comment["content"], comment["created_at"]))
        print("  ✓ 1 Comment inserted")

        # 7. Page Share
        share = generate_page_share(workspace["workspace_id"], page["page_id"], users[1]["user_id"], users[1]["workspace_id"])
        cursor.execute("""
            INSERT INTO notion.page_share (share_id, workspace_id, page_id, shared_with, shared_with_workspace, permission, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (share["share_id"], share["workspace_id"], share["page_id"], share["shared_with"],
              share["shared_with_workspace"], share["permission"], share["created_at"]))
        print("  ✓ Page shared")

        # 8. Page Tag
        page_tag = generate_page_tag(workspace["workspace_id"], page["page_id"], tags[0]["tag_id"])
        cursor.execute("""
            INSERT INTO notion.page_tag (workspace_id, page_id, tag_id)
            VALUES (%s, %s, %s)
        """, (page_tag["workspace_id"], page_tag["page_id"], page_tag["tag_id"]))
        print("  ✓ Page tagged")

        conn.commit()
        print("✅ Done inserting one complete dataset!\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()

    finally:
        cursor.close()


if __name__ == "__main__":
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres"
    )
    print("🔗 Connected to database")
    insert_single_dataset(conn)
    conn.close()
    print("🔌 Connection closed.")
