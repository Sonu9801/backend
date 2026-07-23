import sys
from datetime import datetime
from app.database import SessionLocal, engine, Base
import app.models
from app.models.user import User

def seed_data():
    db = SessionLocal()
    
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    # Check if database already has users
    if db.query(User).first() is not None:
        print("Database already seeded. Skipping.")
        db.close()
        return

    print("Seeding database...")
    
    # Create Default Admin User
    admin_user = User(
        email="admin@foxflow.com",
        name="Admin",
        role="admin",
        is_active=True
    )
    
    # Create Default Operator User
    operator_user = User(
        email="operator@foxflow.com",
        name="Operator",
        role="operator",
        is_active=True
    )
    
    db.add(admin_user)
    db.add(operator_user)
    db.commit()
    db.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    seed_data()
