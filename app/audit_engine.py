"""
Reservation Audit Engine — motor de regras.
Recebe XML (RES_DETAIL / Oracle Reports) e retorna lista de reservas
com issues detectados, risk_score, evidence e suggested_action.
"""

import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Configuração de regras (equivalente ao YAML, inline para simplicidade)
# ---------------------------------------------------------------------------

CORPORATE_RATE_CODES = {"CMP", "CIBMS0", "CNR"}
CORPORATE_MARKET_CODES = {"CMP", "CNR"}
BAR_MARKET_CODES = {"BAR", "MKT"}
WHOLESALE_MARKET_CODES = {"IT"}
DISCOUNT_MARKET_CODES = {"DISC"}

PAYMENT_DIRECT_KEYWORDS = [
    "PGMTO DIRETO", "PGTO DIRETO", "FATURAR DIARIAS",
    "FATUARAR DIARIAS", "EXTRAS PAG DIRETO", "PAGTO VIA LINK",
    "FATURAR DIÁRIAS", "DEBITAR DIARIAS",
]

BILLING_KEYWORDS = [
    "FATURAR", "FATUARAR", "DEBITAR DIARIAS", "FATURAR DIARIAS",
]

RISK_WEIGHTS = {"high": 30, "medium": 15, "low": 5}

# Tolerância (em BRL) para considerar comentário = valor da reserva
COMMENT_VALUE_TOLERANCE_BRL = 0.02


def _text(el, tag):
    """Extrai texto de um sub-elemento; retorna string vazia se ausente."""
    child = el.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _parse_company_name(raw):
    """
    Extrai Company (C-) e Travel Agent / Source (T-) do campo COMPANY_NAME.
    Formato no XML: "C- Nome Empresa\\nT- Nome Agente" ou "C- xxx T- yyy".
    Returns: (company, travel_agent_source)
    """
    if not raw or not raw.strip():
        return ("", "")
    text = raw.replace("\r\n", "\n").strip()
    company = ""
    travel_agent = ""
    # Primeiro tenta por "T-" como separador (C- ... T- ...)
    if "T-" in text:
        parts = text.split("T-", 1)
        c_part = parts[0].strip()
        if c_part.upper().startswith("C-"):
            company = c_part[2:].strip()
        else:
            company = c_part
        travel_agent = parts[1].strip() if len(parts) > 1 else ""
    elif text.upper().startswith("C-"):
        company = text[2:].strip()
    else:
        company = text
    return (company, travel_agent)


def _num(el, tag):
    """Extrai valor numérico; retorna 0.0 se não parseável."""
    raw = _text(el, tag)
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _int_val(el, tag):
    """Extrai inteiro; retorna 0 se não parseável."""
    raw = _text(el, tag)
    try:
        return int(raw)
    except (ValueError, AttributeError):
        return 0


def _parse_date(raw):
    """Tenta interpretar datas nos formatos observados no XML."""
    for fmt in ("%d/%m/%y", "%d-%b-%y", "%d-%B-%y", "%Y%m%d"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _get_comments(resv_el):
    """Retorna lista de textos de RES_COMMENT da reserva."""
    comments = []
    for c in resv_el.iter("G_COMMENT_RESV_NAME_ID"):
        txt = _text(c, "RES_COMMENT")
        if txt:
            comments.append(txt)
    return comments


def _parse_brl_from_text(s):
    """
    Converte string de valor em R$ (BR) para float.
    Aceita: "1.625", "1,625", "1.684,85", "1,684.85", "1625", "1684.85".
    """
    if not s or not isinstance(s, str):
        return None
    s = s.strip().replace(" ", "")
    if not s:
        return None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
            return float(s)
        if "," in s:
            after = s.split(",")[-1]
            if len(after) == 2 and after.isdigit():
                return float(s.replace(",", "."))
            return float(s.replace(",", ""))
        if "." in s:
            after = s.split(".")[-1]
            if len(after) == 2 and after.isdigit():
                return float(s)
            return float(s.replace(".", ""))
        return float(s)
    except (ValueError, AttributeError):
        return None


def _extract_value_from_comment(comments_text):
    """
    Extrai o primeiro valor em R$/BRL encontrado no texto do comentário.
    Padrões: TRF R$ 1,625 + TXS | DIARIA: R$ 1,625 + 5% DE ISS | R$ 1.684,85 | BRL 1625.00
    Retorna (valor_float, trecho_encontrado) ou (None, None).
    """
    if not comments_text:
        return (None, None)
    # Padrões que capturam valor após R$ ou BRL (número com . e ,)
    # TRF R$ 1,625 + TXS | DIARIA: R$ 1,625 + 5% DE ISS | R$ 1.684,85 (CST já tratado em _r015)
    patterns = [
        r"TRF\s*R\$\s*([\d.,]+)",
        r"DIARIA:\s*R\$\s*([\d.,]+)",
        r"R\$\s*([\d.,]+)",
        r"BRL\s*([\d.,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, comments_text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            val = _parse_brl_from_text(raw)
            if val is not None and val >= 0:
                return (val, raw.strip())
    return (None, None)


def _detect_channel(origin, ext_ref, company_name, comments_text):
    """Classifica canal com base nos campos disponíveis."""
    if origin == "GD":
        return "Direct"
    if not ext_ref:
        return "Direct" if origin != "TA" else "OTA Unknown"

    lower_all = (company_name + " " + comments_text).lower()
    if "expedia" in lower_all or "hotels.com" in lower_all:
        return "Expedia Group"
    if "booking.com" in lower_all or "booking" in lower_all:
        return "Booking.com"
    if "omnibees" in lower_all:
        return "Omnibees"

    if origin == "TA":
        return "OTA (TA)"
    return "Unknown"


def _has_keyword(text, keywords):
    upper = text.upper()
    return any(kw.upper() in upper for kw in keywords)


# ---------------------------------------------------------------------------
# Regras individuais — cada uma retorna (issue_code, severity, evidence_dict) ou None
# ---------------------------------------------------------------------------

def _r001_rate_code_ausente(r):
    if not r["rate_code"]:
        return ("RATE_CODE_AUSENTE", "high", {"RATE_CODE": "(vazio)"})

def _r002_fatura_sem_company(r):
    has_billing = _has_keyword(r["comments_text"], BILLING_KEYWORDS)
    if (has_billing or r["comp_house"] == "C") and not r["company_name"]:
        return ("FATURA_SEM_COMPANY_NAME", "high", {
            "COMP_HOUSE": r["comp_house"],
            "COMPANY_NAME": "(vazio)",
            "comentário_billing": has_billing,
        })

def _r003_ota_guarantee_incompativel(r):
    if r["channel"] in ("OTA (TA)", "Expedia Group", "Booking.com", "Omnibees"):
        if r["guarantee_code"] in ("CO", "WV") and not r["company_name"]:
            return ("OTA_GUARANTEE_INCOMPATIVEL", "high", {
                "channel": r["channel"],
                "GUARANTEE_CODE": r["guarantee_code"],
                "COMPANY_NAME": "(vazio)",
            })

def _r004_ext_ref_inconsistente(r):
    if r["origin"] == "TA" and not r["external_reference"]:
        return ("EXT_REF_AUSENTE_TA", "medium", {"ORIGIN_OF_BOOKING": "TA", "EXTERNAL_REFERENCE": "(vazio)"})
    if r["external_reference"]:
        pattern = r"^\d{7,10}-\d{7,10}$"
        if not re.match(pattern, r["external_reference"]):
            return ("EXT_REF_FORMATO_INVALIDO", "medium", {"EXTERNAL_REFERENCE": r["external_reference"]})

def _r005_rate_market_divergencia(r):
    rc = r["rate_code"]
    mc = r["market_code"]
    if not rc or not mc:
        return None
    if mc in BAR_MARKET_CODES and rc in CORPORATE_RATE_CODES:
        return ("RATE_MARKET_DIVERGENCIA", "medium", {"RATE_CODE": rc, "MARKET_CODE": mc})
    if mc in CORPORATE_MARKET_CODES and rc.startswith("HP"):
        return ("RATE_MARKET_DIVERGENCIA", "medium", {"RATE_CODE": rc, "MARKET_CODE": mc})

def _r006_falta_garantia(r):
    if not r["guarantee_code"]:
        return ("GARANTIA_AUSENTE", "high", {"GUARANTEE_CODE": "(vazio)"})

def _r007_comentario_inconsistente(r):
    has_direct = _has_keyword(r["comments_text"], PAYMENT_DIRECT_KEYWORDS)
    has_billing = _has_keyword(r["comments_text"], BILLING_KEYWORDS)
    if has_billing and not r["company_name"]:
        return ("INSTRUCAO_FATURAR_SEM_COMPANY", "high", {
            "RES_COMMENT": r["comments_text"][:120],
            "COMPANY_NAME": "(vazio)",
        })
    if has_direct and r["guarantee_code"] == "CO" and not r["company_name"]:
        return ("PGTO_DIRETO_CO_SEM_COMPANY", "medium", {
            "GUARANTEE_CODE": "CO",
            "COMPANY_NAME": "(vazio)",
            "RES_COMMENT": r["comments_text"][:120],
        })

def _r008_corporativo_sem_company(r):
    is_corp = r["rate_code"] in CORPORATE_RATE_CODES or r["market_code"] in CORPORATE_MARKET_CODES
    if is_corp and not r["company_name"]:
        return ("CORPORATIVO_SEM_COMPANY", "high", {
            "RATE_CODE": r["rate_code"],
            "MARKET_CODE": r["market_code"],
            "COMPANY_NAME": "(vazio)",
        })

def _r009_comp_house_sem_company(r):
    if r["comp_house"] == "C" and not r["company_name"]:
        return ("COMP_HOUSE_SEM_COMPANY", "high", {
            "COMP_HOUSE": "C",
            "COMPANY_NAME": "(vazio)",
        })

def _r010_tarifa_zero(r):
    if r["effective_rate"] == 0:
        has_justification = (
            r["market_code"] in DISCOUNT_MARKET_CODES
            or r["comp_house"] == "C"
            or r["membership_type"]
            or _has_keyword(r["comments_text"], ["cortesia", "comp", "pontos", "reward", "points"])
        )
        if not has_justification:
            return ("TARIFA_ZERO_SEM_JUSTIFICATIVA", "medium", {
                "EFFECTIVE_RATE_AMOUNT": "0",
                "MARKET_CODE": r["market_code"],
            })

def _r011_cc_sem_cartao(r):
    if r["guarantee_code"] == "CC" and not r["credit_card"]:
        return ("CC_SEM_NUMERO_CARTAO", "high", {
            "GUARANTEE_CODE": "CC",
            "CREDIT_CARD_NUMBER": "(vazio)",
        })

def _r013_quarto_nao_atribuido(r):
    if not r["room_no"]:
        return ("QUARTO_NAO_ATRIBUIDO", "medium", {
            "ROOM_NO": "(vazio)",
            "ARRIVAL": r["arrival_raw"],
        })

def _r015_cst_divergente(r):
    match = re.search(r"CST:\s*Quotable Cost\s*:\s*BRL\s*([\d.,]+)", r["comments_text"])
    if match:
        try:
            cst_val = float(match.group(1).replace(",", ""))
        except ValueError:
            return None
        if abs(cst_val - r["effective_rate"]) > 0.01 and cst_val > 0:
            return ("CST_DIVERGENTE", "medium", {
                "CST_Quotable_Cost": str(cst_val),
                "EFFECTIVE_RATE_AMOUNT": str(r["effective_rate"]),
            })

def _r016_payment_method_vs_guarantee(r):
    if r["guarantee_code"] == "CO" and r["payment_method"] in ("MC", "VS", "AX") and not r["company_name"]:
        return ("PAGAMENTO_INCOMPATIVEL_GARANTIA", "medium", {
            "GUARANTEE_CODE": "CO",
            "PAYMENT_METHOD": r["payment_method"],
            "COMPANY_NAME": "(vazio)",
        })
    if r["guarantee_code"] == "CC" and r["payment_method"] == "CA":
        return ("CC_COM_PAGAMENTO_CASH", "medium", {
            "GUARANTEE_CODE": "CC",
            "PAYMENT_METHOD": "CA",
        })


def _r017_comentario_valor_diverge_reserva(r):
    """
    Verifica se o valor citado no comentário (TRF R$ X, DIARIA: R$ X, etc.)
    corresponde ao valor da reserva (EFFECTIVE_RATE_AMOUNT / SHARE_AMOUNT em BRL).
    """
    comment_val, comment_raw = _extract_value_from_comment(r["comments_text"])
    if comment_val is None:
        return None
    # Valor de referência da reserva (BRL)
    res_val = r["effective_rate"] if r["effective_rate"] else r["share_amount"]
    if res_val is None or res_val == 0:
        return None
    diff = abs(comment_val - res_val)
    if diff > COMMENT_VALUE_TOLERANCE_BRL:
        return ("COMENTARIO_VALOR_DIVERGE", "medium", {
            "valor_no_comentario": comment_raw,
            "valor_comentario_BRL": f"{comment_val:.2f}",
            "EFFECTIVE_RATE_AMOUNT": f"{r['effective_rate']:.2f}",
            "SHARE_AMOUNT": f"{r['share_amount']:.2f}",
            "diferenca_BRL": f"{diff:.2f}",
        })

ALL_RULES = [
    _r001_rate_code_ausente,
    _r002_fatura_sem_company,
    _r003_ota_guarantee_incompativel,
    _r004_ext_ref_inconsistente,
    _r005_rate_market_divergencia,
    _r006_falta_garantia,
    _r007_comentario_inconsistente,
    _r008_corporativo_sem_company,
    _r009_comp_house_sem_company,
    _r010_tarifa_zero,
    _r011_cc_sem_cartao,
    _r013_quarto_nao_atribuido,
    _r015_cst_divergente,
    _r016_payment_method_vs_guarantee,
    _r017_comentario_valor_diverge_reserva,
]


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def parse_and_audit(xml_content, target_date=None):
    """
    Parseia XML RES_DETAIL e aplica todas as regras de auditoria.

    Args:
        xml_content: bytes ou string do XML.
        target_date: datetime.date opcional; se None, usa amanhã.

    Returns:
        dict com:
          - total_reservations: int
          - target_date: str
          - records: list[dict] (todas as reservas com issues e sem)
          - summary: dict com contadores
    """
    root = ET.fromstring(xml_content)

    if target_date is None:
        target_date = (datetime.now() + timedelta(days=1)).date()

    all_records = []
    ext_ref_map = {}

    for resv in root.iter("G_RESERVATION"):
        arrival_raw = _text(resv, "ARRIVAL")
        arrival_dt = _parse_date(arrival_raw)

        comments = _get_comments(resv)
        comments_text = " | ".join(comments)

        membership_type = ""
        for mem in resv.iter("G_MEM_TYPE_LEVEL"):
            membership_type = _text(mem, "MEMBERSHIP_TYPE")
            break

        r = {
            "confirmation_no": _text(resv, "CONFIRMATION_NO"),
            "guest_name": _text(resv, "FULL_NAME"),
            "arrival_raw": arrival_raw,
            "arrival_dt": arrival_dt,
            "departure_raw": _text(resv, "DEPARTURE"),
            "room_no": _text(resv, "ROOM_NO") or _text(resv, "DISP_ROOM_NO"),
            "room_category": _text(resv, "ROOM_CATEGORY_LABEL"),
            "rate_code": _text(resv, "RATE_CODE"),
            "market_code": _text(resv, "MARKET_CODE"),
            "guarantee_code": _text(resv, "GUARANTEE_CODE"),
            "payment_method": _text(resv, "PAYMENT_METHOD"),
            "credit_card": _text(resv, "CREDIT_CARD_NUMBER"),
            "company_name": _text(resv, "COMPANY_NAME"),
            "company_parsed": _parse_company_name(_text(resv, "COMPANY_NAME"))[0],
            "travel_agent_source": _parse_company_name(_text(resv, "COMPANY_NAME"))[1],
            "comp_house": _text(resv, "COMP_HOUSE"),
            "origin": _text(resv, "ORIGIN_OF_BOOKING"),
            "external_reference": _text(resv, "EXTERNAL_REFERENCE"),
            "effective_rate": _num(resv, "EFFECTIVE_RATE_AMOUNT"),
            "share_amount": _num(resv, "SHARE_AMOUNT"),
            "currency": _text(resv, "CURRENCY_CODE"),
            "adults": _int_val(resv, "ADULTS"),
            "children": _int_val(resv, "CHILDREN"),
            "status": _text(resv, "SHORT_RESV_STATUS"),
            "products": _text(resv, "PRODUCTS"),
            "special_requests": _text(resv, "SPECIAL_REQUESTS"),
            "deposit_paid": _num(resv, "DEPOSIT_PAID"),
            "membership_type": membership_type,
            "comments": comments,
            "comments_text": comments_text,
            "count_res_comments": _int_val(resv, "COUNT_RES_COMMENTS"),
            "vip": _text(resv, "VIP"),
            "resv_name_id": _text(resv, "RESV_NAME_ID"),
        }

        r["channel"] = _detect_channel(
            r["origin"], r["external_reference"],
            r["company_name"], comments_text,
        )

        # Rastrear external_reference para duplicidade
        if r["external_reference"]:
            ext_ref_map.setdefault(r["external_reference"], []).append(r["confirmation_no"])

        # Aplicar regras
        issues = []
        for rule_fn in ALL_RULES:
            result = rule_fn(r)
            if result:
                code, severity, evidence = result
                issues.append({
                    "code": code,
                    "severity": severity,
                    "evidence": evidence,
                })

        risk_score = min(100, sum(RISK_WEIGHTS.get(i["severity"], 0) for i in issues))

        actions = []
        for i in issues:
            actions.append(_suggested_action(i["code"]))

        r["detected_issues"] = issues
        r["risk_score"] = risk_score
        r["suggested_actions"] = actions
        r["issue_codes"] = [i["code"] for i in issues]

        all_records.append(r)

    # Regra de duplicidade (R014) — pós-processamento
    dup_refs = {ref: confs for ref, confs in ext_ref_map.items() if len(confs) > 1}
    for rec in all_records:
        if rec["external_reference"] in dup_refs:
            others = [c for c in dup_refs[rec["external_reference"]] if c != rec["confirmation_no"]]
            issue = {
                "code": "DUPLICIDADE_EXT_REF",
                "severity": "high",
                "evidence": {
                    "EXTERNAL_REFERENCE": rec["external_reference"],
                    "outras_confirmacoes": ", ".join(others),
                },
            }
            rec["detected_issues"].append(issue)
            rec["issue_codes"].append("DUPLICIDADE_EXT_REF")
            rec["suggested_actions"].append(_suggested_action("DUPLICIDADE_EXT_REF"))
            rec["risk_score"] = min(100, rec["risk_score"] + RISK_WEIGHTS["high"])

    # Ordenar por risk_score desc
    all_records.sort(key=lambda x: (-x["risk_score"], x["confirmation_no"]))

    total = len(all_records)
    with_issues = sum(1 for r in all_records if r["detected_issues"])
    high_count = sum(1 for r in all_records if any(i["severity"] == "high" for i in r["detected_issues"]))
    medium_count = sum(1 for r in all_records if any(i["severity"] == "medium" for i in r["detected_issues"]) and not any(i["severity"] == "high" for i in r["detected_issues"]))
    clean_count = total - with_issues

    return {
        "total_reservations": total,
        "target_date": str(target_date),
        "records": all_records,
        "summary": {
            "total": total,
            "with_issues": with_issues,
            "high_risk": high_count,
            "medium_risk": medium_count,
            "clean": clean_count,
        },
    }


def _suggested_action(code):
    ACTIONS = {
        "RATE_CODE_AUSENTE": "Preencher RATE_CODE no PMS.",
        "FATURA_SEM_COMPANY_NAME": "Incluir COMPANY_NAME para faturamento.",
        "OTA_GUARANTEE_INCOMPATIVEL": "Ajustar garantia conforme política do canal.",
        "EXT_REF_AUSENTE_TA": "Incluir EXTERNAL_REFERENCE para conciliação.",
        "EXT_REF_FORMATO_INVALIDO": "Corrigir formato de EXTERNAL_REFERENCE.",
        "RATE_MARKET_DIVERGENCIA": "Conferir RATE_CODE vs MARKET_CODE.",
        "GARANTIA_AUSENTE": "Incluir código de garantia.",
        "INSTRUCAO_FATURAR_SEM_COMPANY": "Comentário indica faturar empresa mas COMPANY_NAME está vazio.",
        "PGTO_DIRETO_CO_SEM_COMPANY": "Garantia CO com pagamento direto sem empresa.",
        "CORPORATIVO_SEM_COMPANY": "Reserva corporativa sem COMPANY_NAME.",
        "COMP_HOUSE_SEM_COMPANY": "Company house (C) sem COMPANY_NAME.",
        "TARIFA_ZERO_SEM_JUSTIFICATIVA": "Tarifa zero sem justificativa; verificar.",
        "CC_SEM_NUMERO_CARTAO": "Garantia CC sem número de cartão.",
        "QUARTO_NAO_ATRIBUIDO": "Atribuir quarto antes do check-in.",
        "CST_DIVERGENTE": "CST Quotable Cost diverge de EFFECTIVE_RATE.",
        "PAGAMENTO_INCOMPATIVEL_GARANTIA": "Método de pagamento incompatível com garantia.",
        "CC_COM_PAGAMENTO_CASH": "Garantia CC mas pagamento em dinheiro.",
        "DUPLICIDADE_EXT_REF": "Referência externa duplicada; verificar duplicidade de reserva.",
        "COMENTARIO_VALOR_DIVERGE": "Valor no comentário (TRF/DIARIA/R$) não confere com EFFECTIVE_RATE_AMOUNT/SHARE_AMOUNT; conferir no PMS.",
    }
    return ACTIONS.get(code, "Verificar manualmente.")
