import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.api.schemas.expenses_schema import ExtractedExpense

load_dotenv()

api_key_env = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key_env)

def analyze_receipt_image(image_bytes: bytes, mime_type: str) -> ExtractedExpense:
    """
    Sends the receipt image to Gemini 1.5 Flash to extract structured financial data.
    """
    system_prompt = """Actúa como un extractor de datos financieros. Analiza la imagen y extrae la información en formato JSON estricto.

            CATEGORÍAS:
            - "Medicamentos": Farmacias (Salcobrand, Cruz Verde, etc.) o compra de remedios.
            - "Abarrotes": Supermercados (Jumbo, Lider, fruteria, verduleria, etc.) o productos de alimentación/hogar.
            - "Sueldos": Transferencias bancarias a personas o pago de remuneraciones.
            - "Otros": Todo lo que no encaje en lo anterior.

            FORMATO DE SALIDA (Solo JSON):
            {
            "amount": float,
            "currency": "CLP" | "USD",
            "merchant": "nombre del comercio o destinatario",
            "date": "YYYY-MM-DD",
            "category": "Medicamentos" | "Abarrotes" | "Sueldos" | "Otros",
            "description": "descripción corta del gasto"
            }

            REGLAS:
1. MONTO: Extrae el TOTAL FINAL a pagar (el monto más grande o el que dice "TOTAL", "Total", "Neto a pagar"). NO uses descuentos, ahorros, subtotales, IVA, ni propinas.
2. ATENCIÓN: Los montos pueden usar punto como separador de miles (ej: "$6.026" = 6026, "$1.500" = 1500). Ignora los puntos y toma el número completo.
3. Si hay múltiples totales, elige el que corresponda al monto final a pagar.
4. Categoría: Si no estás seguro, asigna "Otros"."""

    response = client.models.generate_content(
        model='models/gemini-2.0-flash-lite',
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            system_prompt
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": ExtractedExpense,
            "temperature": 0.1
        }
    )
    
    raw = response.text
    if raw is None:
        raise ValueError("Gemini returned empty response")
    return ExtractedExpense.model_validate_json(raw)

