from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

from app.config import settings
from app.routers.health import router as health_router
from app.routers.fitness import router as fitness_router
from app.routers.plan import router as plan_router
from app.routers.voice import router as voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nextbite")

app = FastAPI(
    title="NextBite API",
    description="NextBite AI-Powered Meal Recommendation & Nutrition Assistant Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware with strict origin enforcement
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Middleware for standard protection headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Include API Routers
app.include_router(health_router)
app.include_router(fitness_router)
app.include_router(plan_router)
app.include_router(voice_router)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting NextBite API in {settings.ENVIRONMENT} mode...")
    logger.info(f"GCP Project: {settings.PROJECT_ID} | Gemini Model: {settings.GEMINI_MODEL}")
    if settings.GEMINI_API_KEY:
        logger.info("Gemini API Key configured and verified.")
    else:
        logger.warning("Gemini API Key not found. Operating with nutritional grounding engine.")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development")
    )
