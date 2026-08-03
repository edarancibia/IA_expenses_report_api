import zipfile
import io
import re
import time
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import fitz
from app.api.services.ai_provider import analyze_receipt_image

CATEGORY_EMOJIS = {
    "Sueldos": "🟢",
    "Abarrotes": "🟡",
    "Medicamentos": "🔵",
    "Otros": "🟠",
}

REPORT_NOTICE = (
    '- Todas las transferencias bancarias se consideran "Sueldos" automáticamente a menos que el detalle del comprobante indique otro tipo de gasto.\n'
    "- Los montos son extraídos automáticamente por IA y podrían contener errores. Se recomienda revisar cada comprobante antes de usar estos datos para fines contables."
)

def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[Tuple[bytes, str]]:
    pages = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("jpeg")
        pages.append((img_bytes, "image/jpeg"))
    doc.close()
    return pages

def get_date_range(report_type: str, start: Optional[date] = None, end: Optional[date] = None) -> Tuple[date, date]:
    today = date.today()

    if report_type == "monthly":
        return today - timedelta(days=30), today
    elif report_type == "custom" and start and end:
        return start, end
    return today - timedelta(days=7), today

def get_file_date(zip_file: zipfile.ZipFile, filename: str) -> date:
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
    if match:
        return date(*map(int, match.groups()))
    
    zip_info = zip_file.getinfo(filename)
    return date(zip_info.date_time[0], zip_info.date_time[1], zip_info.date_time[2])

def filter_files_by_date(unique_images: List[str], start_date: date, end_date: date) -> List[str]:
    """Filtra una lista de nombres de archivos según una fecha mínima."""
    date_pattern = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
    filtered = []
    
    for img_name in unique_images:
        match = date_pattern.search(img_name)
        if match:
            try:
                year, month, day = map(int, match.groups())
                file_date = date(year, month, day)
                #if file_date >= start_date:
                if start_date <= file_date <= end_date:
                    filtered.append(img_name)
            except ValueError:
                continue
    return filtered

def process_zip_file(
    zip_content: bytes, 
    report_type: str = "custom", 
    start_date_input: Optional[date] = None, 
    end_date_input: Optional[date] = None
) -> Dict[str, Any]:
    """
    Procesa un archivo ZIP, filtra archivos (JPG/PNG/PDF) según fecha del nombre o del sistema.
    """
    s_date, e_date = get_date_range(report_type, start_date_input, end_date_input)
    
    processed_expenses = []
    
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
        file_list = zip_file.namelist()
        valid_extensions = ('.jpg', '.jpeg', '.png', '.pdf')
        
        potential_files = [f for f in file_list if f.lower().endswith(valid_extensions)]
        
        filtered_files = []
        for f_name in potential_files:
            file_date = get_file_date(zip_file, f_name)
            if s_date <= file_date <= e_date:
                filtered_files.append(f_name)

        print(f"DEBUG: Periodo: {s_date} a {e_date}")
        print(f"DEBUG: Archivos filtrados para procesar: {len(filtered_files)}")
        
        for img_name in filtered_files:
            file_bytes = zip_file.read(img_name)

            try:
                if img_name.lower().endswith('.pdf'):
                    page_images = pdf_to_images(file_bytes)
                    for page_idx, (page_bytes, _) in enumerate(page_images):
                        expense = analyze_receipt_image(page_bytes, "image/jpeg")
                        label = f"{img_name} (pág {page_idx + 1})"
                        print(f"[{label}] ${expense.amount:,.0f} | {expense.merchant} | {expense.category}")
                        if expense.amount > 0:
                            exp_data = expense.model_dump()
                            exp_data["_filename"] = img_name
                            processed_expenses.append(exp_data)
                        else:
                            print(f"  ↳ Descartado (sin total visible)")
                        time.sleep(1)
                else:
                    mime_type = "image/png" if img_name.lower().endswith('.png') else "image/jpeg"
                    expense = analyze_receipt_image(file_bytes, mime_type)
                    print(f"[{img_name}] ${expense.amount:,.0f} | {expense.merchant} | {expense.category}")
                    if expense.amount > 0:
                        exp_data = expense.model_dump()
                        exp_data["_filename"] = img_name
                        processed_expenses.append(exp_data)
                    else:
                        print(f"  ↳ Descartado (sin total visible)")
                    time.sleep(1)
            except Exception as e:
                print(f"Error procesando {img_name}: {str(e)}")
                continue
        
        for exp in processed_expenses:
            name_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", exp.get("_filename", ""))
            if name_match:
                exp["date"] = f"{name_match.group(1)}-{name_match.group(2)}-{name_match.group(3)}"

        dedup_count = deduplicate_expenses(processed_expenses)
        if dedup_count > 0:
            print(f"  ↳ {dedup_count} duplicado(s) eliminado(s)")

        filtered_count = filter_small_items(processed_expenses)
        if filtered_count > 0:
            print(f"  ↳ {filtered_count} item(es) individual(es) descartados (< 15% del total del día)")

        for exp in processed_expenses:
            exp.pop("_filename", None)
        summary = generate_expenses_summary(processed_expenses, s_date, e_date)
        report = generate_ai_report(processed_expenses, summary)

    return {
        "status": "Procesamiento completado",
        "total_read_vouchers": len(processed_expenses),
        "summary": summary,
        "expenses": processed_expenses,
        "report": report
    }

def filter_small_items(expenses: List[Dict[str, Any]]) -> int:
    groups: Dict[Tuple[str, str], List[int]] = {}
    for i, exp in enumerate(expenses):
        key = (exp.get("date", ""), exp.get("category", ""))
        groups.setdefault(key, []).append(i)
    to_remove = set()
    for key, indices in groups.items():
        amounts = [expenses[i].get("amount", 0) or 0 for i in indices]
        max_amt = max(amounts)
        max_idx = amounts.index(max_amt)
        max_min = _filename_to_minute(expenses[indices[max_idx]].get("_filename", ""))
        for idx, amt in zip(indices, amounts):
            if max_amt > 0 and amt / max_amt < 0.15 and amt != max_amt:
                curr_min = _filename_to_minute(expenses[idx].get("_filename", ""))
                if abs(curr_min - max_min) <= 5:
                    print(f"  ↳ Descartado: ${amt:,.0f} | {expenses[idx].get('merchant','')} (vs ${max_amt:,.0f})")
                    to_remove.add(idx)
    for idx in sorted(to_remove, reverse=True):
        expenses.pop(idx)
    return len(to_remove)

def _filename_to_minute(name: str) -> int:
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})", name)
    if not match:
        return 0
    return int(match.group(4)) * 60 + int(match.group(5))

def deduplicate_expenses(expenses: List[Dict[str, Any]]) -> int:
    seen = {}
    to_remove = set()
    for i, exp in enumerate(expenses):
        amount = exp.get("amount", 0) or 0
        key = (exp.get("date"), exp.get("category"), round(amount / 100) * 100)
        if key in seen:
            prev = expenses[seen[key]]
            prev_min = _filename_to_minute(prev.get("_filename", ""))
            curr_min = _filename_to_minute(exp.get("_filename", ""))
            if abs(curr_min - prev_min) <= 10:
                prev_len = len(prev.get("merchant", ""))
                curr_len = len(exp.get("merchant", ""))
                if curr_len > prev_len:
                    to_remove.add(seen[key])
                    seen[key] = i
                else:
                    to_remove.add(i)
            else:
                seen[key] = i
        else:
            seen[key] = i
    for idx in sorted(to_remove, reverse=True):
        expenses.pop(idx)
    return len(to_remove)

def generate_expenses_summary(
    processed_expenses: List[Dict[str, Any]],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:

    temp_totals = {}

    for expense in processed_expenses:
        amount = expense.get("amount") or 0.0
        category = expense.get("category", "Others")
        
        temp_totals[category] = temp_totals.get(category, 0.0) + amount

    category_list = [
        {"category": cat, "total": total} 
        for cat, total in temp_totals.items()
    ]

    period_str = ""
    if start_date and end_date:
        period_str = f"{start_date.strftime('%d-%m-%Y')} al {end_date.strftime('%d-%m-%Y')}"

    return {
        "period": period_str,
        "total_amount": sum(item["total"] for item in category_list),
        "category_breakdown": category_list,
        "count": len(processed_expenses)
    }

def _fmt_amount(amount: float) -> str:
    return f"${amount:,.0f}"

def generate_ai_report(
    processed_expenses: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> str:
    lines = ["🤖 REPORTE GENERADO CON IA", "📊 RESUMEN DE GASTOS"]
    lines.append(f"📅 Periodo: {summary.get('period', '')}")
    lines.append("Detalle por categoría:")

    category_order = [item["category"] for item in summary["category_breakdown"]]
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for exp in processed_expenses:
        grouped.setdefault(exp.get("category", "Otros"), []).append(exp)

    for category in category_order:
        expenses = grouped.get(category, [])
        emoji = CATEGORY_EMOJIS.get(category, "⚪")
        cat_total = next(
            (item["total"] for item in summary["category_breakdown"] if item["category"] == category),
            0.0,
        )
        lines.append(f"{emoji} {category} — {_fmt_amount(cat_total)}")
        for i, exp in enumerate(expenses):
            branch = "┗" if i == len(expenses) - 1 else "┣"
            amount_str = _fmt_amount(exp.get("amount", 0.0))
            merchant = exp.get("merchant", "")
            lines.append(f"   {branch} {amount_str:<8} ─ {merchant}")

    separator = "━" * 17
    lines.append(separator)
    lines.append(f"💰 TOTAL: {_fmt_amount(summary.get('total_amount', 0.0))}")
    lines.append(separator)
    lines.append("⚠️ Aviso:")
    lines.append(REPORT_NOTICE)

    return "\n".join(lines)