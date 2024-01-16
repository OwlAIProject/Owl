from fastapi import FastAPI
from .capture import router as capture_router
from .capture_socket import socket_app 


app = FastAPI()

app.mount("/socket.io", socket_app)

app.include_router(capture_router)

@app.get("/")
def read_root():
    return "UntitledAI is running!"
