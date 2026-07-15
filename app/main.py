from fastapi import FastAPI

app = FastAPI(
    title="Central Stock Management System",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "Welcome to the Central Stock Management System API!"
    }
