from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes.whatsapp import router as whatsapp_router
from app.routes import admin

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(whatsapp_router)
app.include_router(admin.router)

@app.get("/status")
async def get_status():
    return {"status": "WhatsApp Bot is running", "environment": "development"}

@app.get("/")
async def health_check():
    return {"status": "WhatsApp Bot API is running"}
