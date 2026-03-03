# 7 (b). Esboço de payloads de entrada/saída — Automação

## Entrada (upload do XML)

**Método:** POST  
**Content-Type:** multipart/form-data  

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| file  | binary (arquivo) | Sim | Arquivo XML com root `RES_DETAIL` e estrutura `LIST_G_GROUP_BY1` > `G_GROUP_BY1` > `LIST_G_RESERVATION` > `G_RESERVATION`. |

**Query params opcionais:**

- `format`: `json` | `csv` (default: json)
- `min_risk_score`: 0–100 (default: 0)
- `include_clean`: boolean (default: false) — incluir reservas sem issues

**Exemplo de chamada (conceitual):**

```
POST /audit/v1/audit?format=json&min_risk_score=20
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="res_detail4383227.xml"
Content-Type: application/xml

<?xml version="1.0" encoding="UTF-8"?>
<RES_DETAIL>
  <LIST_G_GROUP_BY1>...</LIST_G_GROUP_BY1>
</RES_DETAIL>
------WebKitFormBoundary--
```

---

## Saída — JSON (application/json)

**200 OK**

```json
{
  "audit_run_id": "20260302-a1b2c3d4",
  "source_file": "res_detail4383227.xml",
  "generated_at": "2026-03-02T10:00:00Z",
  "total_reservations": 25,
  "reservations_with_issues": 8,
  "records": [
    {
      "confirmation_no": "1553333",
      "guest_name": "Luz,Amanda,Miss",
      "channel": "Direct",
      "rate_code": "CMP",
      "market_code": "CMP",
      "detected_issues": ["MISSING_COMPANY_NAME", "COMP_HOUSE_NO_COMPANY"],
      "suggested_action": "Incluir COMPANY_NAME para reserva company house (COMP_HOUSE=C).",
      "risk_score": 85,
      "evidence": {
        "COMP_HOUSE": "C",
        "COMPANY_NAME": "",
        "GUARANTEE_CODE": "CO"
      }
    }
  ]
}
```

---

## Saída — CSV (text/csv)

**200 OK**  
**Content-Type:** text/csv; charset=utf-8  

Colunas: confirmation_no, guest_name, channel, rate_code, market_code, detected_issues, suggested_action, risk_score, evidence  

(detected_issues e evidence em uma única célula; listas separadas por ponto-e-vírgula ou equivalente configurável.)

---

## Códigos de erro esperados

| HTTP | code (body)        | Quando usar |
|------|--------------------|-------------|
| 400  | INVALID_INPUT      | Arquivo ausente, não XML ou XML malformado (não parseável). |
| 413  | PAYLOAD_TOO_LARGE  | Tamanho do arquivo acima do limite (ex.: 50 MB). |
| 422  | UNRECOGNIZED_STRUCTURE | XML válido mas sem RES_DETAIL ou sem nenhum G_RESERVATION. |
| 500  | INTERNAL_ERROR     | Falha inesperada no processamento. |

**Exemplo de corpo de erro:**

```json
{
  "code": "INVALID_INPUT",
  "message": "Arquivo não é um XML válido ou não contém elemento RES_DETAIL."
}
```

---

*Estes payloads permitem automação (scripts, integrações) sem depender da implementação interna do motor de auditoria.*
