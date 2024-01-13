from fastapi import FastAPI
from .capture import router as capture_router

app = FastAPI()

app.include_router(capture_router)

@app.get("/")
def read_root():
    return "UntitledAI is running!"