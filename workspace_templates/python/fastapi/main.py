from fastapi import FastAPI

app = FastAPI(title="My FastAPI App")

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI!"}

@app.get("/health")
async def health():
    return {"status": "ok"}
