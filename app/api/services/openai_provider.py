import os
import base64
import json

from openai import OpenAI
from openai import RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.api.schemas.expenses_schema import ExtractedExpense

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

SYSTEM_PROMPT = """
Actúa como un extractor de datos financieros. Analiza la imagen y extrae la información en formato JSON estricto.

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
4. Categoría: Si no estás seguro, asigna "Otros".
"""

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type(RateLimitError)
)
def _call_openai_with_retry(base64_image: str, mime_type: str):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extrae la información."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )

def analyze_receipt_image_openai(
    image_bytes: bytes,
    mime_type: str
) -> ExtractedExpense:

    base64_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    response = _call_openai_with_retry(base64_image, mime_type)
    content = response.choices[0].message.content

    if content is None:
        raise ValueError("OpenAI returned empty response")

    return ExtractedExpense.model_validate_json(content)