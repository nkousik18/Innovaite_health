"""
Quick fix for relationship issues
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from config import get_settings

async def check_and_fix():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        # Check if alert_subscriptions table has proper foreign key
        result = await conn.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'alert_subscriptions'
        """)
        
        print("\n=== Alert Subscriptions Table Columns ===")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
    
    await engine.dispose()
    print("\n✅ Check complete!")

if __name__ == "__main__":
    asyncio.run(check_and_fix())