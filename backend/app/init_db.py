# Import models first so SQLAlchemy registers their tables.
from app import models
from app.database import Base, engine

Base.metadata.create_all(bind=engine)
print("Database tables are ready.")