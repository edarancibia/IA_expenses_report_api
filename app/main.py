from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Aquí importarás el enrutador global cuando lo tengas creado
from app.api.api import api_router

# 1. Inicializar la aplicación de FastAPI
app = FastAPI(
    title="API de Reportes de Gastos Familiares",
    description="Backend en FastAPI para procesar comprobantes de WhatsApp con IA",
    version="1.0.0",
)

# 2. Configurar Middlewares (CORS) - CRUCIAL PARA REACT
# Esto permite que tu futuro frontend en React (que correrá en otro puerto)
# pueda hacer peticiones a esta API sin recibir bloqueos de seguridad.
origins = [
    "http://localhost:3000",      # Puerto estándar de React local
    "http://localhost:5173",      # Puerto estándar si usas Vite + React
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # Autoriza los orígenes de la lista
    allow_credentials=True,
    allow_methods=["*"],             # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],             # Permite todos los headers
)

# 3. Ruta de prueba (Health Check)
@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "mensaje": "Servidor de Reportes Familiares funcionando correctamente 🚀"
    }

# 4. Conectar las rutas globales de la API
# Cuando crees tu archivo app/api/v1/api.py, descomentas esta línea:
app.include_router(api_router, prefix="/api/v1")