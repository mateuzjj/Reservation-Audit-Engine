# 3. Taxonomia de rate codes — Reservation Audit Engine

Agrupamento e nomenclatura das categorias de rate code observadas no XML, com indicadores (palavras-chave, padrões, campos relacionados) e regras de consistência esperadas (descritas em linguagem natural; sem implementação).

---

## 3.1 Rate codes observados no XML

Valores únicos de **RATE_CODE** na amostra:

- **HPPRP1**, **HPPBB1** — prefixo HP (Hilton Program?) + sufixo (RP, BB).
- **CMP** — idêntico a MARKET_CODE CMP; tipicamente corporate/company.
- **FW** — possivelmente Flex/Wholesale ou similar.
- **CIBMS0** — padrão “CI” + “BMS” + número; corporate/IBM observado em COMPANY_NAME.
- **TCSBI2** — TCS + BI + número; consórcio/consortia (MARKET_CODE CONS).
- **HHNSRR** — HH (Hilton Honors) + NSRR (Non-Stay Reward?); MARKET_CODE DISC.
- **ODBB23** — ODBB + número; MARKET_CODE IT (Individual Tour?).
- **WH2** — Wholesale; MARKET_CODE IT.
- **L9** — código curto; MARKET_CODE LNR (Local Negotiated Rate?).
- **PGBB01**, **OGBKBB** — PG/OGBK + BB; MARKET_CODE MKT.

---

## 3.2 Categorias e indicadores

### INDIVIDUAL TOUR / WHOLESALE

| Item | Descrição |
|------|------------|
| **Indicadores** | RATE_CODE contém ou igual a: `WH2`, `ODBB23`, `FW` (quando associado a MARKET_CODE IT). MARKET_CODE = IT. |
| **Campos relacionados** | MARKET_CODE (IT), ORIGIN_OF_BOOKING (TA comum), EXTERNAL_REFERENCE presente. |
| **Exemplo no XML** | `<RATE_CODE>WH2</RATE_CODE>` + `<MARKET_CODE>IT</MARKET_CODE>`; `<RATE_CODE>ODBB23</RATE_CODE>` + `<MARKET_CODE>IT</MARKET_CODE>`. |
| **Regras de consistência** | Tarifa não deve ser zero sem comentário explicativo. Para OTA/wholesale, GUARANTEE_CODE normalmente CC ou equivalente; CO/CD sem company pode indicar inconsistência. |

---

### CORPORATE NEGOTIATED / CORPORATE MARKETING PROGRAM

| Item | Descrição |
|------|------------|
| **Indicadores** | RATE_CODE como `CIBMS0`, `CMP`; MARKET_CODE CNR, CMP. COMPANY_NAME preenchido com padrão "C- ... T- ..." (Company / Travel agent). |
| **Campos relacionados** | COMPANY_NAME, MARKET_CODE (CNR, CMP), GUARANTEE_CODE (CC ou CO). |
| **Exemplo no XML** | `<RATE_CODE>CIBMS0</RATE_CODE>` + `<MARKET_CODE>CNR</MARKET_CODE>` + `<COMPANY_NAME>C- I B M\nT- Flytour Business T</COMPANY_NAME>`. `<RATE_CODE>CMP</RATE_CODE>` + `<MARKET_CODE>CMP</MARKET_CODE>`. |
| **Regras de consistência** | Reserva com rate corporativo deve ter COMPANY_NAME preenchido. COMP_HOUSE = C deve ter COMPANY_NAME. GUARANTEE_CODE CO (company) deve ter COMPANY_NAME. |

---

### CONSORTIA

| Item | Descrição |
|------|------------|
| **Indicadores** | MARKET_CODE = CONS; RATE_CODE como `TCSBI2` (prefixos TCS/BI). |
| **Campos relacionados** | MARKET_CODE (CONS), EXTERNAL_REFERENCE, ORIGIN_OF_BOOKING (GD observado). |
| **Exemplo no XML** | `<MARKET_CODE>CONS</MARKET_CODE>` + `<RATE_CODE>TCSBI2</RATE_CODE>` + `<ORIGIN_OF_BOOKING>GD</ORIGIN_OF_BOOKING>`. |
| **Regras de consistência** | COMPANY_NAME pode estar presente (consórcio/agente). Garantia e instrução de pagamento alinhadas ao contrato (ex.: CC ou CO). |

---

### LOCAL NEGOTIATED RATE (LNR)

| Item | Descrição |
|------|------------|
| **Indicadores** | MARKET_CODE = LNR; RATE_CODE curto como `L9`. |
| **Campos relacionados** | MARKET_CODE LNR, GUARANTEE_CODE (CO, CD observados). |
| **Exemplo no XML** | `<MARKET_CODE>LNR</MARKET_CODE>` + `<RATE_CODE>L9</RATE_CODE>`. |
| **Regras de consistência** | Se GUARANTEE_CODE = CO ou faturamento empresa, COMPANY_NAME obrigatório. |

---

### OTHER DISCOUNTS / LOYALTY (DISC)

| Item | Descrição |
|------|------------|
| **Indicadores** | MARKET_CODE = DISC; RATE_CODE como `HHNSRR` (Hilton Honors). |
| **Campos relacionados** | LIST_G_MEM_TYPE_LEVEL (HH), EFFECTIVE_RATE_AMOUNT pode ser 0 (pontos). |
| **Exemplo no XML** | `<MARKET_CODE>DISC</MARKET_CODE>` + `<RATE_CODE>HHNSRR</RATE_CODE>` + `<EFFECTIVE_RATE_AMOUNT>0</EFFECTIVE_RATE_AMOUNT>` + membro HH. |
| **Regras de consistência** | Tarifa zero aceitável quando há programa de fidelidade; caso contrário verificar comentário ou garantia. |

---

### BAR / RACK / MARKET (MKT, BAR)

| Item | Descrição |
|------|------------|
| **Indicadores** | MARKET_CODE = MKT ou BAR; RATE_CODE como `HPPRP1`, `HPPBB1`, `PGBB01`, `OGBKBB`. |
| **Campos relacionados** | PAYMENT_METHOD, GUARANTEE_CODE (CC comum), EFFECTIVE_RATE_AMOUNT > 0. |
| **Exemplo no XML** | `<MARKET_CODE>BAR</MARKET_CODE>` + `<RATE_CODE>HPPRP1</RATE_CODE>`; `<MARKET_CODE>MKT</MARKET_CODE>` + `<RATE_CODE>PGBB01</RATE_CODE>`. |
| **Regras de consistência** | RATE_CODE e MARKET_CODE devem ser coerentes (ex.: BAR com rate de bar; MKT com rate de mercado). Divergência entre os dois pode indicar tarifa incorreta. |

---

### PAGAMENTO DIRETO / FATURAMENTO DIRETO (indicado por comentários)

| Item | Descrição |
|------|------------|
| **Indicadores** | RES_COMMENT contém: "PGMTO DIRETO", "PGTO DIRETO", "FATURAR DIARIAS", "FATUARAR DIARIAS", "EXTRAS PAG DIRETO", "PAGTO VIA LINK". Não é rate code em si; é instrução de pagamento. |
| **Campos relacionados** | COMPANY_NAME (pode estar preenchido para fatura empresa), GUARANTEE_CODE, PAYMENT_METHOD. |
| **Exemplo no XML** | `<RES_COMMENT>PGMTO DIRETO +  EXTRAS</RES_COMMENT>`, `<RES_COMMENT>FATURAR DIARIAS + TAXAS // EXTRAS PAG DIRETO</RES_COMMENT>`. |
| **Regras de consistência** | Comentário "faturar empresa" ou "FATURAR DIARIAS" sem COMPANY_NAME é inconsistente. GUARANTEE_CODE CO com comentário "pagamento direto" exige clarificação. |

---

### CONFIDENCIAL / CÓDIGOS GENÉRICOS

| Item | Descrição |
|------|------------|
| **Indicadores** | RATE_CODE ou MARKET_CODE com valores que não se enquadram nas categorias acima; ou listas configuráveis "confidenciais" / "outros". |
| **Regras de consistência** | Validar presença de garantia e, se aplicável, COMPANY_NAME. |

---

## 3.3 Regras de consistência entre RATE_CODE e MARKET_CODE (resumo)

- **RATE_CODE = CMP** → MARKET_CODE esperado CMP ou compatível corporativo.
- **MARKET_CODE = CNR** → RATE_CODE tipicamente corporativo (ex.: CIBMS0); COMPANY_NAME esperado.
- **MARKET_CODE = IT** → RATE_CODE wholesale/tour (WH2, ODBB23, FW).
- **MARKET_CODE = CONS** → RATE_CODE tipo TCSBI2 ou similar consórcio.
- **MARKET_CODE = LNR** → RATE_CODE negociado (ex.: L9); se CO/CD, COMPANY_NAME esperado.
- **MARKET_CODE = DISC** → RATE_CODE pode ser HHNSRR ou outro desconto; tarifa zero aceitável com programa.
- **MARKET_CODE = MKT/BAR** → RATE_CODE não deve ser claramente corporativo/wholesale sem justificativa.

Divergência forte entre RATE_CODE e MARKET_CODE (ex.: MARKET_CODE BAR com RATE_CODE CIBMS0) deve gerar alerta de auditoria.

---

*Taxonomia inferida a partir dos valores presentes no XML fornecido. Listas de rate codes por categoria e thresholds devem ser parametrizáveis em configuração.*
