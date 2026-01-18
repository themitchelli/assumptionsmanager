from fastapi import FastAPI

app = FastAPI(title="Assumptions Manager", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "Hello from Assumptions Manager!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "ok"}
