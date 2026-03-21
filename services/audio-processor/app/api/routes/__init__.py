from .detect import router as detect_router
from .generate import router as generate_router
from .arrange import router as arrange_router

__all__ = [
    "detect_router",
    "generate_router", 
    "arrange_router",
]
