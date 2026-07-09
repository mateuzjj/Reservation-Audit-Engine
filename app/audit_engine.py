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
KNOWN_MARKET_CODES = {
    "BAR", "CMP", "CNR", "CONS", "DISC", "IT", "LNR", "MKT",
    "CMTG", "SMRF", "HOU", "GOV",
}

# Rate codes / empresas para seleção de template de comentário
BOOKING_REFUNDABLE_RATES = {"OGBKBB"}
BOOKING_NONREFUND_RATES = {"2D"}
EXPEDIA_RATES = {"PGHCP1"}
OMNIBEES_RATES = {"L4"}
POINTS_HH_RATES = {"HHNSRR"}
GROUP_RATES = {"GRXG3", "GRXG4", "GRXG5"}
WEBBEDS_RATES = {"WH0"}
HOTELBEDS_RATES = {"WH2", "WH3"}
COOBRASTUR_RATES = {"WHC"}
DESPEGAR_RATES = {"J5"}
SPC_RATES = {"SPC"}

VALID_GUARANTEE_CODES = {"CC", "CO", "CD", "WV", "6P", "CASH", "CHECKED IN"}

PAYMENT_DIRECT_KEYWORDS = [
    "PGMTO DIRETO", "PGTO DIRETO", "FATURAR DIARIAS",
    "FATUARAR DIARIAS", "EXTRAS PAG DIRETO", "PAGTO VIA LINK",
    "FATURAR DIÁRIAS", "DEBITAR DIARIAS",
]

BILLING_KEYWORDS = [
    "FATURAR", "FATUARAR", "DEBITAR DIARIAS", "FATURAR DIARIAS",
]

RISK_WEIGHTS = {"high": 30, "medium": 15, "low": 5}

# Tolerância para comparação de valores: 5% ou R$10, o que for maior
COMMENT_VALUE_TOLERANCE_PCT = 0.05
COMMENT_VALUE_TOLERANCE_MIN_BRL = 10.0
CST_TOLERANCE_PCT = 0.05
CST_TOLERANCE_MIN_BRL = 10.0


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


def _detect_channel(origin, ext_ref, company_name, comments_text, routing_text=""):
    """Classifica canal com base nos campos disponíveis."""
    if origin == "GC":
        return "Group/Conference"
    if origin == "GD":
        return "Direct"
    if not ext_ref and origin != "TA":
        return "Direct"

    lower_all = (company_name + " " + comments_text + " " + routing_text).lower()
    if "expedia" in lower_all or "hotels.com" in lower_all or "amex online thc" in lower_all or "hotels com" in lower_all:
        return "Expedia Group"
    if "booking.com" in lower_all or "booking com" in lower_all:
        return "Booking.com"
    if "omnibees" in lower_all or "99 tecnologia" in lower_all:
        return "Omnibees"
    if "hotelbeds" in lower_all or "webbeds" in lower_all or "sunhotels" in lower_all:
        return "Wholesaler"
    if "despegar" in lower_all:
        return "Despegar"
    if "ctrip" in lower_all or "agoda" in lower_all or "shanghai huacheng" in lower_all:
        return "Asia OTA"

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

def _is_cortesia_cmp(r):
    rc = (r["rate_code"] or "").upper()
    mc = (r["market_code"] or "").upper()
    return "CMP" in rc or "COMP" in rc or "CMP" in mc or "COMP" in mc

def _r002_fatura_sem_company(r):
    if _is_cortesia_cmp(r):
        return None
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
    gc = r["guarantee_code"]
    if not gc:
        return ("GARANTIA_AUSENTE", "high", {"GUARANTEE_CODE": "(vazio)"})
    if gc not in VALID_GUARANTEE_CODES:
        return ("GARANTIA_DESCONHECIDA", "low", {"GUARANTEE_CODE": gc})

def _r007_comentario_inconsistente(r):
    if _is_cortesia_cmp(r):
        return None
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
    if _is_cortesia_cmp(r):
        return None
    is_corp = r["rate_code"] in CORPORATE_RATE_CODES or r["market_code"] in CORPORATE_MARKET_CODES
    if is_corp and not r["company_name"]:
        return ("CORPORATIVO_SEM_COMPANY", "high", {
            "RATE_CODE": r["rate_code"],
            "MARKET_CODE": r["market_code"],
            "COMPANY_NAME": "(vazio)",
        })

def _r009_comp_house_sem_company(r):
    if _is_cortesia_cmp(r):
        return None
    if r["comp_house"] == "C" and not r["company_name"]:
        return ("COMP_HOUSE_SEM_COMPANY", "high", {
            "COMP_HOUSE": "C",
            "COMPANY_NAME": "(vazio)",
        })

def _r010_tarifa_zero(r):
    if r["effective_rate"] == 0:
        has_justification = (
            r["is_shared"]
            or "CMP" in r["rate_code"].upper()
            or "COMP" in r["rate_code"].upper()
            or "HOU" in r["rate_code"].upper()
            or "CMP" in r["market_code"].upper()
            or "COMP" in r["market_code"].upper()
            or "HOU" in r["market_code"].upper()
            or r["market_code"] in DISCOUNT_MARKET_CODES
            or r["comp_house"] == "C"
            or r["membership_type"]
            or _has_keyword(r["comments_text"], ["cortesia", "comp", "pontos", "reward", "points"])
        )
        if not has_justification:
            return ("TARIFA_ZERO_SEM_JUSTIFICATIVA", "medium", {
                "EFFECTIVE_RATE_AMOUNT": "0",
                "RATE_CODE": r["rate_code"],
                "MARKET_CODE": r["market_code"],
            })

def _r011_cc_sem_cartao(r):
    if r["guarantee_code"] == "CC" and not r["credit_card"]:
        return ("CC_SEM_NUMERO_CARTAO", "high", {
            "GUARANTEE_CODE": "CC",
            "CREDIT_CARD_NUMBER": "(vazio)",
        })


def _r015_cst_divergente(r):
    match = re.search(r"CST:\s*Quotable Cost\s*:\s*BRL\s*([\d.,]+)", r["comments_text"])
    if match:
        try:
            cst_val = float(match.group(1).replace(",", ""))
        except ValueError:
            return None
        if cst_val <= 0:
            return None
        # CST é custo total da estadia — comparar com SHARE_AMOUNT primeiro
        ref_val = r["share_amount"] if r["share_amount"] > 0 else r["effective_rate"]
        if ref_val <= 0:
            return None
        diff = abs(cst_val - ref_val)
        tolerance = max(CST_TOLERANCE_MIN_BRL, ref_val * CST_TOLERANCE_PCT)
        if diff > tolerance:
            return ("CST_DIVERGENTE", "medium", {
                "CST_Quotable_Cost": f"{cst_val:.2f}",
                "SHARE_AMOUNT": f"{r['share_amount']:.2f}",
                "EFFECTIVE_RATE_AMOUNT": f"{r['effective_rate']:.2f}",
                "diferenca_BRL": f"{diff:.2f}",
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
    corresponde ao valor da reserva. Compara com SHARE_AMOUNT (total estadia)
    primeiro, depois com EFFECTIVE_RATE_AMOUNT (diária).
    """
    comment_val, comment_raw = _extract_value_from_comment(r["comments_text"])
    if comment_val is None or comment_val <= 0:
        return None
    # Comparar com SHARE_AMOUNT primeiro (TRF geralmente é valor total)
    share = r["share_amount"]
    rate = r["effective_rate"]
    if share > 0:
        diff_share = abs(comment_val - share)
        tol_share = max(COMMENT_VALUE_TOLERANCE_MIN_BRL, share * COMMENT_VALUE_TOLERANCE_PCT)
        if diff_share <= tol_share:
            return None  # Confere com share_amount
    if rate > 0:
        diff_rate = abs(comment_val - rate)
        tol_rate = max(COMMENT_VALUE_TOLERANCE_MIN_BRL, rate * COMMENT_VALUE_TOLERANCE_PCT)
        if diff_rate <= tol_rate:
            return None  # Confere com effective_rate
    # Não confere com nenhum
    ref_val = share if share > 0 else rate
    if ref_val <= 0:
        return None
    diff = min(
        abs(comment_val - share) if share > 0 else float('inf'),
        abs(comment_val - rate) if rate > 0 else float('inf'),
    )
    return ("COMENTARIO_VALOR_DIVERGE", "medium", {
        "valor_no_comentario": comment_raw,
        "valor_comentario_BRL": f"{comment_val:.2f}",
        "SHARE_AMOUNT": f"{share:.2f}",
        "EFFECTIVE_RATE_AMOUNT": f"{rate:.2f}",
        "diferenca_BRL": f"{diff:.2f}",
    })

def _r012_ota_sem_ext_ref(r):
    if r["channel"] in ("OTA (TA)", "Expedia Group", "Booking.com", "Omnibees",
                         "Wholesaler", "Despegar", "Asia OTA") and not r["external_reference"]:
        return ("OTA_SEM_EXT_REF", "medium", {
            "channel": r["channel"],
            "EXTERNAL_REFERENCE": "(vazio)",
        })

def _r018_cartao_expirado(r):
    is_cc_guarantee = r["guarantee_code"] == "CC" or r["payment_method"] in ("VS", "MC", "AX", "DC", "VI", "CA", "AE")
    if r["exp_date"] == "EXP" or (is_cc_guarantee and not r["exp_date"] and r["credit_card"]):
        return ("CARTAO_VALIDADE_PENDENTE", "medium", {
            "EXP_DATE": r["exp_date"] or "(vazio/ausente)",
            "PAYMENT_METHOD": r["payment_method"],
            "CREDIT_CARD_NUMBER": r["credit_card"] or "(vazio)",
        })

def _r019_market_code_ausente(r):
    if not r["market_code"]:
        return ("MARKET_CODE_AUSENTE", "medium", {"MARKET_CODE": "(vazio)"})

def _r020_datas_invalidas(r):
    arr = r["arrival_dt"]
    dep = r["departure_dt"]
    if arr is None and r["arrival_raw"]:
        return ("DATA_ARRIVAL_INVALIDA", "high", {"ARRIVAL": r["arrival_raw"]})
    if dep is None and r["departure_raw"]:
        return ("DATA_DEPARTURE_INVALIDA", "high", {"DEPARTURE": r["departure_raw"]})
    if arr and dep and dep < arr:
        return ("DEPARTURE_ANTES_ARRIVAL", "high", {
            "ARRIVAL": r["arrival_raw"],
            "DEPARTURE": r["departure_raw"],
        })

def _r022_multiplos_trf_divergentes(r):
    trfs = re.findall(r"TRF R\$\s*([\d.,]+)", r["comments_text"])
    if len(trfs) > 1:
        vals = set()
        for raw in trfs:
            v = _parse_brl_from_text(raw)
            if v is not None:
                vals.add(round(v, 2))
        if len(vals) > 1:
            return ("MULTIPLOS_TRF_DIVERGENTES", "medium", {
                "valores_TRF": ", ".join(f"R${v:.2f}" for v in sorted(vals)),
                "quantidade": str(len(vals)),
            })

def _r024_rate_share_divergencia(r):
    rate = r["effective_rate"]
    share = r["share_amount"]
    if rate > 0 and share > 0:
        diff = abs(rate - share)
        tol = max(10.0, rate * 0.05)
        if diff > tol:
            return ("RATE_SHARE_DIVERGENCIA", "medium", {
                "EFFECTIVE_RATE_AMOUNT": f"{rate:.2f}",
                "SHARE_AMOUNT": f"{share:.2f}",
                "diferenca": f"{diff:.2f}",
            })

def _r025_booking_sem_comentario_cobranca(r):
    if r["channel"] == "Booking.com" and r["deposit_paid"] == 0:
        has_charging = (
            re.search(r"TRF\s*(?:R\$\s*)?[\d.,]+", r["comments_text"], re.IGNORECASE)
            or re.search(r"DIARIA:\s*R\$\s*[\d.,]+", r["comments_text"], re.IGNORECASE)
            or re.search(r"PGMTO\s+DIRETO|PAGTO\s+DIRETO|PGTO\s+DIRETO", r["comments_text"], re.IGNORECASE)
        )
        if not has_charging:
            return ("BOOKING_SEM_COMENTARIO_COBRANCA", "medium", {
                "channel": "Booking.com",
                "DEPOSIT_PAID": "0.00",
                "SHARE_AMOUNT": f"{r['share_amount']:.2f}",
                "CREDIT_CARD_NUMBER": r["credit_card"] or "(vazio)",
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
    _r012_ota_sem_ext_ref,
    _r015_cst_divergente,
    _r016_payment_method_vs_guarantee,
    _r017_comentario_valor_diverge_reserva,
    _r018_cartao_expirado,
    _r019_market_code_ausente,
    _r020_datas_invalidas,
    _r022_multiplos_trf_divergentes,
    _r024_rate_share_divergencia,
    _r025_booking_sem_comentario_cobranca,
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
        departure_raw = _text(resv, "DEPARTURE")
        departure_dt = _parse_date(departure_raw)

        # Calcular número de noites
        num_nights = 0
        if arrival_dt and departure_dt and departure_dt > arrival_dt:
            num_nights = (departure_dt - arrival_dt).days

        comments = _get_comments(resv)
        comments_text = " | ".join(comments)

        membership_type = ""
        for mem in resv.iter("G_MEM_TYPE_LEVEL"):
            membership_type = _text(mem, "MEMBERSHIP_TYPE")
            break

        # Routing info (LIST_G_BILL_RESV)
        routing_parts = []
        for bill in resv.iter("G_BILL_RESV"):
            trx = _text(bill, "TRX_STRING")
            if trx:
                routing_parts.append(trx)
        routing_text = " | ".join(routing_parts)

        r = {
            "confirmation_no": _text(resv, "CONFIRMATION_NO"),
            "guest_name": _text(resv, "FULL_NAME"),
            "arrival_raw": arrival_raw,
            "arrival_dt": arrival_dt,
            "departure_raw": departure_raw,
            "departure_dt": departure_dt,
            "num_nights": num_nights,
            "room_no": _text(resv, "ROOM_NO") or _text(resv, "DISP_ROOM_NO"),
            "room_category": _text(resv, "ROOM_CATEGORY_LABEL"),
            "rate_code": _text(resv, "RATE_CODE"),
            "market_code": _text(resv, "MARKET_CODE"),
            "guarantee_code": _text(resv, "GUARANTEE_CODE"),
            "payment_method": _text(resv, "PAYMENT_METHOD"),
            "credit_card": _text(resv, "CREDIT_CARD_NUMBER"),
            "exp_date": _text(resv, "EXP_DATE"),
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
            "is_shared": _text(resv, "IS_SHARED_YN") == "Y",
            "block_code": _text(resv, "BLOCK_CODE"),
            "group_id": _text(resv, "GROUP_ID"),
            "routing_text": routing_text,
        }

        r["channel"] = _detect_channel(
            r["origin"], r["external_reference"],
            r["company_name"], comments_text, routing_text,
        )

        # Rastrear external_reference para duplicidade (com info de sharer)
        if r["external_reference"]:
            ext_ref_map.setdefault(r["external_reference"], []).append({
                "conf": r["confirmation_no"],
                "is_shared": r["is_shared"],
                "room_no": r["room_no"],
            })

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
            actions.append(_suggested_action(i["code"], r))

        r["detected_issues"] = issues
        r["risk_score"] = risk_score
        r["suggested_actions"] = actions
        r["suggested_opera_comment"] = _generate_ready_comment(r)
        r["issue_codes"] = [i["code"] for i in issues]

        all_records.append(r)

    # Regra de duplicidade (R014) — pós-processamento com filtro de sharers
    dup_refs = {ref: entries for ref, entries in ext_ref_map.items() if len(entries) > 1}
    for rec in all_records:
        if rec["external_reference"] in dup_refs:
            entries = dup_refs[rec["external_reference"]]
            others = [e["conf"] for e in entries if e["conf"] != rec["confirmation_no"]]
            if not others:
                continue
            # Verificar se todos são sharers (IS_SHARED_YN ou mesmo quarto)
            all_shared = all(e["is_shared"] for e in entries)
            same_room = len(set(e["room_no"] for e in entries if e["room_no"])) <= 1
            if all_shared or same_room:
                continue  # Sharers legítimos — não são duplicidades!
            severity = "high"
            issue = {
                "code": "DUPLICIDADE_EXT_REF",
                "severity": severity,
                "evidence": {
                    "EXTERNAL_REFERENCE": rec["external_reference"],
                    "outras_confirmacoes": ", ".join(others),
                    "sharers": "sim" if (all_shared or same_room) else "não",
                },
            }
            rec["detected_issues"].append(issue)
            rec["issue_codes"].append("DUPLICIDADE_EXT_REF")
            rec["suggested_actions"].append(_suggested_action("DUPLICIDADE_EXT_REF", rec))
            rec["risk_score"] = min(100, rec["risk_score"] + RISK_WEIGHTS[severity])

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


def _generate_ready_comment(r):
    """
    Gera o texto de comentário sugerido pronto para colar no Opera PMS
    com base no canal, empresa, rate_code e valores da reserva.
    Baseado na análise de 5.387 reservas de produção.
    Retorna dict com chaves 'res' (Reservation) e 'inh' (In-house).
    """
    if not r:
        return ""
    val = r["share_amount"] if r.get("share_amount", 0) > 0 else r.get("effective_rate", 0)
    val_str = f"{val:,.2f}"
    rate_str = f"{r.get('effective_rate', 0):,.2f}"
    channel = r.get("channel", "")
    comp = r.get("company_name", "")
    comp_parsed = r.get("company_parsed", "")
    comments_txt = r.get("comments_text", "")
    rc = r.get("rate_code", "")
    mc = r.get("market_code", "")
    cc_last4 = r.get("credit_card", "")[-4:] if r.get("credit_card") else ""
    adults = r.get("adults", 1)

    # --- 1. Pontos HH (HHNSRR) ---
    if rc in POINTS_HH_RATES or "FULL POINTS" in comments_txt.upper():
        return "RSV FULL POINTS // EXTRAS DIRETO"

    # --- 2. Reserva com depósito / balance (pagamento antecipado) ---
    if r.get("deposit_paid", 0) > 0:
        return (f"TARIFA NAO REEMBOLSAVEL // PAG ANTECIPADO DE DIARIAS "
                f"// EXTRAS PAG DIRETO | TRF R$ {val_str} + TXS")

    # --- 3. Group/Conference ---
    if channel == "Group/Conference" or r.get("origin") == "GC":
        tipo = "DPL" if adults >= 2 else "SGL"
        block = r.get("block_code", "")
        pm_ref = f"PM {block}" if block else "PM DO GRUPO"
        return (f"DIÁRIAS {tipo}S PAGAS PELA EMPRESA NA {pm_ref} "
                f"// CONSUMOS EXTRAS SÃO PGTO DIRETO PELOS HÓSPEDES "
                f"| TRF {tipo} R$ {rate_str} + 5% iss")

    # --- 3. Booking.com ---
    if channel == "Booking.com":
        is_nonrefund = (
            rc in BOOKING_NONREFUND_RATES
            or mc == "DISC"
            or any(k in comments_txt.upper() for k in [
                "REEMBOLSAVEL", "REEMBOLSÁVEL", "ANTECIPADO", "NON REF",
            ])
        )
        if is_nonrefund:
            return (f"TARIFA NAO REEMBOLSAVEL // PAG ANTECIPADO DE DIARIAS "
                    f"// EXTRAS PAG DIRETO | TRF R$ {val_str} + TXS")
        return f"PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"

    # --- 4. Expedia Group / Amex ---
    if channel == "Expedia Group":
        return (f"TARIFA CONF // FATURAR DIARIAS + TAXAS "
                f"// EXTRAS PAG DIRETO | TRF R$ {val_str} + TXS")

    # --- 5. Omnibees / 99 Tecnologia ---
    if channel == "Omnibees" or rc in OMNIBEES_RATES:
        return f"PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"

    # --- 6. Asia OTA (Agoda, Ctrip) ---
    if channel == "Asia OTA":
        if cc_last4:
            return (f"TARIFA CONF / DEBITAR DIARIAS + TAXAS NO CC FINAL {cc_last4} "
                    f"// EXTRAS PAG DIRETO | Diaria: R$ {rate_str} + Taxas")
        return (f"TARIFA CONF // FATURAR DIARIAS + TAXAS "
                f"// EXTRAS PAG DIRETO | Diaria: R$ {rate_str} + Taxas")

    # --- 7. Despegar ---
    if channel == "Despegar" or rc in DESPEGAR_RATES:
        if cc_last4:
            return (f"TARIFA CONF / DEBITAR DIARIAS + TAXAS NO CC FINAL {cc_last4} "
                    f"// EXTRAS PAG DIRETO | Diaria: R$ {rate_str} + Taxas")
        return (f"TARIFA CONF // FATURAR DIARIAS + TAXAS "
                f"// EXTRAS PAG DIRETO | TRF R$ {val_str} + TXS")

    # --- 8. Wholesaler: WEBBEDS (WH0, IT) — débito no CC ---
    if "WEBBEDS" in comp.upper() or rc in WEBBEDS_RATES:
        if cc_last4:
            return (f"TARIFA CONF / DEBITAR DIARIAS + TAXAS NO CC FINAL {cc_last4} "
                    f"// EXTRAS PAG DIRETO | Diaria: R$ {rate_str} + Taxas")
        return (f"TARIFA CONF // FATURAR DIARIAS + TAXAS "
                f"// EXTRAS PAG DIRETO | Diaria: R$ {rate_str} + Taxas")

    # --- 9. Wholesaler: HOTELBEDS (WH2/WH3, IT) — faturar ---
    if "HOTELBEDS" in comp.upper() or rc in HOTELBEDS_RATES:
        return (f"TARIFA CONF // FATURAR DIARIAS + TAXAS "
                f"// EXTRAS PAG DIRETO | TRF R$ {val_str} + TXS")

    # --- 10. Wholesaler: COOBRASTUR (WHC, IT) — ISS explícito ---
    if "COOBRASTUR" in comp.upper() or rc in COOBRASTUR_RATES:
        return (f"TARIFA CONF // FATURAR DIARIAS + 5% DE ISS "
                f"// EXTRAS PAG DIRETO | DIARIA: R$ {rate_str} + 5% DE ISS")

    # --- 11. Wholesaler genérico (IT) ---
    if mc == "IT" and comp:
        return (f"TARIFA CONF // FATURAR DIARIAS + TAXAS "
                f"// EXTRAS PAG DIRETO | TRF R$ {val_str} + TXS")

    # --- 12. Corporativo com empresa (CIBMS0, CNR) ---
    if (rc in CORPORATE_RATE_CODES or mc in CORPORATE_MARKET_CODES) and comp:
        return f"PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"

    # --- 13. OTA (TA) genérico ---
    if channel == "OTA (TA)":
        return f"PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"

    # --- 14. Company billing (com empresa + indicação de faturar) ---
    if comp and (r.get("comp_house") == "C" or any(
        k in comments_txt.upper() for k in ["FATURAR", "FATUARAR"]
    )):
        return f"FATURAR DIARIAS E TAXAS PARA {comp_parsed or comp} // EXTRAS DIRETO"

    # --- 15. SPC tarifa especial ---
    if rc in SPC_RATES:
        return f"PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"

    # --- 16. Fallback genérico ---
    if val > 0:
        return f"PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"

    return ""


def _suggested_action(code, r=None):
    val = 0.0
    val_str = "0.00"
    if r:
        val = r["share_amount"] if r.get("share_amount", 0) > 0 else r.get("effective_rate", 0)
        val_str = f"{val:,.2f}"

    if code == "BOOKING_SEM_COMENTARIO_COBRANCA":
        return f"Inserir nos comentários do Opera: PGMTO DIRETO + EXTRAS | TRF R$ {val_str} + TXS"
    if code == "COMENTARIO_VALOR_DIVERGE":
        return f"Ajustar comentário de cobrança no Opera para o valor da estadia: TRF R$ {val_str} + TXS"
    if code == "CST_DIVERGENTE":
        return f"CST difere da estadia (R$ {val_str}). Conferir e ajustar comentário no Opera: TRF R$ {val_str} + TXS"
    if code == "INSTRUCAO_FATURAR_SEM_COMPANY":
        return "Vincular COMPANY_NAME no Opera e ajustar comentário: FATURAR DIARIAS E TAXAS PARA [EMPRESA] // EXTRAS DIRETO"
    if code == "FATURA_SEM_COMPANY_NAME":
        return "Vincular COMPANY_NAME no Opera para faturamento da estadia."
    if code == "OTA_GUARANTEE_INCOMPATIVEL":
        channel = r.get("channel", "OTA") if r else "OTA"
        return f"Canal {channel}: ajustar garantia no Opera conforme voucher e política de cobrança."
    if code == "RATE_CODE_AUSENTE":
        return "Preencher código de tarifa (RATE_CODE) no Opera PMS."
    if code == "GARANTIA_AUSENTE":
        return "Preencher código de garantia (GUARANTEE_CODE) no Opera PMS."
    if code in ("CARTAO_EXPIRADO", "CARTAO_VALIDADE_PENDENTE"):
        return "Validade do cartão ausente ou constando como EXP; conferir e inserir validade (MM/AA) no Opera PMS."
    if code == "DUPLICIDADE_EXT_REF":
        ref = r.get("external_reference", "") if r else ""
        return f"Referência externa {ref} duplicada em outra reserva; conferir duplicidade no PMS."

    ACTIONS = {
        "RATE_CODE_AUSENTE": "Preencher RATE_CODE no PMS.",
        "FATURA_SEM_COMPANY_NAME": "Incluir COMPANY_NAME para faturamento.",
        "OTA_GUARANTEE_INCOMPATIVEL": "Ajustar garantia conforme política do canal.",
        "EXT_REF_AUSENTE_TA": "Incluir EXTERNAL_REFERENCE para conciliação.",
        "EXT_REF_FORMATO_INVALIDO": "Corrigir formato de EXTERNAL_REFERENCE.",
        "RATE_MARKET_DIVERGENCIA": "Conferir RATE_CODE vs MARKET_CODE.",
        "GARANTIA_AUSENTE": "Incluir código de garantia.",
        "GARANTIA_DESCONHECIDA": "Código de garantia não reconhecido; verificar.",
        "INSTRUCAO_FATURAR_SEM_COMPANY": "Comentário indica faturar empresa mas COMPANY_NAME está vazio.",
        "PGTO_DIRETO_CO_SEM_COMPANY": "Garantia CO com pagamento direto sem empresa.",
        "CORPORATIVO_SEM_COMPANY": "Reserva corporativa sem COMPANY_NAME.",
        "COMP_HOUSE_SEM_COMPANY": "Company house (C) sem COMPANY_NAME.",
        "TARIFA_ZERO_SEM_JUSTIFICATIVA": "Tarifa zero sem justificativa; verificar.",
        "CC_SEM_NUMERO_CARTAO": "Garantia CC sem número de cartão.",
        "OTA_SEM_EXT_REF": "Reserva OTA sem referência externa; incluir para conciliação.",
        "CST_DIVERGENTE": "CST Quotable Cost diverge do valor da estadia; conferir no PMS.",
        "PAGAMENTO_INCOMPATIVEL_GARANTIA": "Método de pagamento incompatível com garantia.",
        "CC_COM_PAGAMENTO_CASH": "Garantia CC mas pagamento em dinheiro.",
        "DUPLICIDADE_EXT_REF": "Referência externa duplicada; verificar duplicidade de reserva.",
        "COMENTARIO_VALOR_DIVERGE": "Valor no comentário (TRF/DIARIA/R$) diverge do valor da estadia; conferir no PMS.",
        "CARTAO_EXPIRADO": "Data de validade ausente ou constando como EXP; conferir e inserir manualmente no PMS para evitar recusa na cobrança.",
        "CARTAO_VALIDADE_PENDENTE": "Data de validade ausente ou constando como EXP; conferir e inserir manualmente no PMS para evitar recusa na cobrança.",
        "MARKET_CODE_AUSENTE": "MARKET_CODE vazio; preencher no PMS.",
        "DATA_ARRIVAL_INVALIDA": "Data de chegada em formato inválido.",
        "DATA_DEPARTURE_INVALIDA": "Data de saída em formato inválido.",
        "DEPARTURE_ANTES_ARRIVAL": "Data de saída anterior à chegada; corrigir datas.",
        "MULTIPLOS_TRF_DIVERGENTES": "Múltiplos valores de TRF R$ no comentário; verificar valor correto.",
        "RATE_SHARE_DIVERGENCIA": "EFFECTIVE_RATE × noites diverge de SHARE_AMOUNT; verificar tarifa.",
        "BOOKING_SEM_COMENTARIO_COBRANCA": "Reserva Booking sem depósito em conta; ajustar os comentários inserindo o valor a ser cobrado no cartão que consta na reserva (ex: TRF R$ [valor] + TXS).",
    }
    return ACTIONS.get(code, "Verificar manualmente.")
