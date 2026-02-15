"""
Create database tables
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from models.base import Base
from config import get_settings

async def create_tables():
    """Create all tables"""
    settings = get_settings()
    
    # Create engine
    engine = create_async_engine(
        settings.database_url,
        echo=True
    )
    
    try:
        print("Creating tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())