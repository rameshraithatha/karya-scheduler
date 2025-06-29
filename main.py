from fastapi import FastAPI
from api.routes import router as job_router
from api.actions import router as actions_router
from api.mock_routes import router as mock_router
from db.init_db import init_db
import uvicorn

# Initialize DB (for dev/testing)
init_db()

# Create FastAPI app
app = FastAPI()

# Include routers
app.include_router(job_router)
app.include_router(actions_router)
app.include_router(mock_router)

# Start app via CLI
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
