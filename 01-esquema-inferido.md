# 1. Esquema inferido — Reservation Audit Engine

Documento gerado a partir da análise do XML `res_detail4383227.xml` (Oracle Reports 12.2.1.4.0). Estrutura hierárquica e campos detectados com tipo estimado, presença e exemplos.

---

## 1.1 Estrutura hierárquica

```
RES_DETAIL (raiz)
└── LIST_G_GROUP_BY1
    └── G_GROUP_BY1 (repetível; agrupamento por data de chegada)
        ├── GROUPBY1_SORT_COL, GROUPBY1_COL, GROUPBY1_LABEL
        ├── LIST_G_RESERVATION
        │   └── G_RESERVATION (uma ocorrência por reserva)
        │       ├── [campos escalares da reserva]
        │       ├── LIST_G_MEM_TYPE_LEVEL → G_MEM_TYPE_LEVEL (membresias)
        │       ├── LIST_G_INV_ITEMS
        │       ├── LIST_G_BILL_RESV
        │       ├── LIST_G_COMMENT_NAME_ID
        │       ├── LIST_G_RESERV_PROMO
        │       ├── LIST_G_DEPT_ID
        │       ├── LIST_G_DEP_DATE_CHANGE
        │       ├── LIST_G_COMMENT_RESV_NAME_ID → G_COMMENT_RESV_NAME_ID (comentários)
        │       ├── LIST_G_FIXED_CHARGES
        │       └── LIST_G_AWARDS
        ├── ADL_ARRIVAL, RMS_ARRIVAL, CHL_ARRIVAL
        └── CF_GROUPBY1_TOTAL_DESC, CS_DISPLAY_GROUP
└── RMS_REPORT, LOGO, SUM_ADULTS, SUM_CHILDREN, SUM_ROOMS
```

---

## 1.2 Mapeamento de todos os campos detectados

### Nível RES_DETAIL (raiz)

| Nó | Tipo estimado | Presença | Exemplos |
|----|----------------|----------|----------|
| LIST_G_GROUP_BY1 | elemento (lista) | 1 | — |
| RMS_REPORT | string/número | 1 | `23` |
| LOGO | string | 0..1 | `` (vazio) |
| SUM_ADULTS | número | 1 | `27` |
| SUM_CHILDREN | número | 1 | `4` |
| SUM_ROOMS | número | 1 | `23` |

### Nível G_GROUP_BY1 (agrupamento por chegada)

| Nó | Tipo estimado | Presença | Exemplos |
|----|----------------|----------|----------|
| GROUPBY1_SORT_COL | string | 1 | `20260302` |
| GROUPBY1_COL | string (data) | 1 | `02/03/26` |
| GROUPBY1_LABEL | string | 1 | `Arrival Date` |
| LIST_G_RESERVATION | elemento (lista) | 1 | — |
| ADL_ARRIVAL | número | 1 | `27` |
| RMS_ARRIVAL | número | 1 | `23` |
| CHL_ARRIVAL | número | 1 | `4` |
| CF_GROUPBY1_TOTAL_DESC | string | 1 | `Arrival Date Total` |
| CS_DISPLAY_GROUP | número | 1 | `25` |

### Nível G_RESERVATION (reserva) — campos escalares

| Nó | Tipo estimado | Presença | Exemplos |
|----|----------------|----------|----------|
| REDEEM_FLAG_YN | string (Y/N) | 0..1 | `` |
| MOBILE_REGSITERED_YN | string (Y/N) | 0..1 | `` |
| TOTAL_STAYS_ACROSS_CHAIN | string | 0..1 | `` |
| TOTAL_NIGHTS_ACROSS_CHAIN | string | 0..1 | `` |
| **EXTERNAL_REFERENCE** | string | 0..1 | `3431187369-425194957`, `3424811981-425906982` |
| UPDATE_DATE | string (data) | 0..1 | `02-MAR-26` |
| UPDATE_USER | string | 0..1 | `1271`, `1491` |
| DISP_ROOM_NO | string | 0..1 | `1301`, `0703`, `` |
| RESV_COLOR | string | 0..1 | `` |
| ROWNUM | número | 0..1 | `20`, `21` |
| IS_SHARED_YN | string (Y/N) | 0..1 | `N` |
| TRUNC_BEGIN | string (data) | 0..1 | `02-MAR-26` |
| TRUNC_END | string (data) | 0..1 | `06-MAR-26` |
| **CONFIRMATION_NO** | string | 1 | `1553114`, `1553333` |
| **ARRIVAL** | string (data) | 1 | `02/03/26` |
| PRODUCTS | string | 0..1 | `TT`, `CONT BREAK BRL`, `BKF2`, `` |
| **SHORT_RESV_STATUS** | string | 1 | `CC`, `CO`, `CD`, `WV`, `6P` |
| RESORT | string | 1 | `GRUJA` |
| FULL_NAME_NO_SHR_IND | string | 1 | `Canclini,Julie Helene Lucie` |
| ARRIVAL_TIME1 | string (hora) | 0..1 | `00:00`, `03:00` |
| ARRIVAL_TRANSPORT_TYPE | string | 0..1 | `` |
| **FULL_NAME** | string | 1 | `Canclini,Julie Helene Lucie` |
| NO_OF_ROOMS | número | 1 | `1` |
| ROOM_CATEGORY_LABEL | string | 1 | `D2`, `K1`, `K1T`, `K1SC` |
| ARRIVAL_TIME | string (hora) | 0..1 | `00:00`, `03:00`, `` |
| DEPARTURE_TIME | string | 0..1 | `` |
| **MARKET_CODE** | string | 1 | `BAR`, `CMP`, `CNR`, `CONS`, `DISC`, `IT`, `LNR`, `MKT` |
| **RATE_CODE** | string | 1 | `HPPRP1`, `CMP`, `FW`, `CIBMS0`, `TCSBI2`, `HHNSRR`, `ODBB23`, `WH2`, `L9`, `PGBB01`, `HPPBB1`, `OGBKBB` |
| **DEPARTURE** | string (data) | 1 | `06/03/26`, `03/03/26` |
| VIP | string | 0..1 | `` |
| **GUARANTEE_CODE** | string | 1 | `CC`, `CO`, `CD`, `WV`, `6P` |
| BILL_TO_ADDRESS | string (multilinha) | 0..1 | `Steen Billes Gade 1, Copenhague`, `` |
| PREFERRED_ROOM_TYPE | string | 0..1 | `` |
| BEGIN_DATE | string (data) | 0..1 | `02-MAR-26` |
| GROUP_ID | string | 0..1 | `` |
| BLOCK_CODE | string | 0..1 | `` |
| **ORIGIN_OF_BOOKING** | string | 1 | `TA`, `GD` |
| EFFECTIVE_RATE_AMOUNT | número/decimal | 1 | `1684.85`, `0`, `545`, `1487.7` |
| SPECIAL_REQUESTS | string | 0..1 | `AE,HF,KB,NS`, `BKF`, `` |
| **EXP_DATE** | string | 0..1 | `XX/XX`, `` |
| **PAYMENT_METHOD** | string | 1 | `MC`, `CA`, `VS`, `AX` |
| ADULTS | número | 1 | `1`, `2` |
| CHILDREN | número | 1 | `0`, `2` |
| PERSONS | número | 1 | `1`, `4` |
| DEPOSIT_PAID | número | 0..1 | `0` |
| ARRIVAL_CARRIER_CODE | string | 0..1 | `` |
| **COMPANY_NAME** | string (multilinha) | 0..1 | `C- Hilton Honors Disc\nT- Tumlare Corporatio`, `` |
| CURRENCY_CODE | string | 1 | `BRL` |
| **ROOM_NO** | string | 0..1 | `1301`, `0703`, `` (vazio se não atribuído) |
| SHARE_AMOUNT | número/decimal | 1 | `1684.85`, `0`, `545` |
| **CREDIT_CARD_NUMBER** | string | 0..1 | `XXXX2557`, `` |
| PHYSICAL_QUANTITY | número | 0..1 | `1` |
| RESV_NAME_ID | string | 1 | `1633295` |
| GUEST_NAME_ID | string | 1 | `1426847` |
| PREFERENCES | string | 0..1 | `SM`, `NS`, `` |
| LAST_ROOM | string | 0..1 | `` |
| SHARE_NAMES | string | 0..1 | `` |
| ACCOMPANYING_YN | string (Y/N) | 0..1 | `N` |
| **COMP_HOUSE** | string | 0..1 | `C`, `` |
| ACCOMPANYING_NAMES | string | 0..1 | `` |
| EXTN_NUMBER | string | 0..1 | `` |
| ADVANCE_CHECKED_IN_YN | string | 0..1 | `` |
| SHOW_AWARDS_LAMP_YN | string (Y/N) | 0..1 | `N` |
| NO_OF_STAYS | número | 0..1 | `0` |
| NO_OF_NIGHTS | número | 0..1 | `0` |
| COUNT_ROUTING | número | 0..1 | `0` |
| **COUNT_COMMENTS** | número | 0..1 | `0` |
| **COUNT_RES_COMMENTS** | número | 0..1 | `0`, `1`, `2` |
| COUNT_PROMOTIONS | número | 0..1 | `0` |
| COUNT_TRACES | número | 0..1 | `0` |
| COUNT_FIXED_CHARGES | número | 0..1 | `0` |
| COUNT_MEMBER_TYPE | número | 0..1 | `0`, `1` |
| COUNT_INVENTORY_ITEMS | string/número | 0..1 | `` |
| COUNT_DEP_DATE_CHANGE | número | 0..1 | `0` |
| CF_COLOR_DESC | string | 0..1 | `` |
| CF_DISPLAY_RECORD_01 | número | 0..1 | `1` |
| CF_ADULTS | número | 0..1 | `1`, `2` |
| CF_CHILDREN | número | 0..1 | `0` |
| CF_NO_OF_ROOMS | número | 0..1 | `1` |

### Nível G_MEM_TYPE_LEVEL (membresia)

| Nó | Tipo estimado | Presença | Exemplos |
|----|----------------|----------|----------|
| RESV_NAME_ID1 | string | 1 | `1633295` |
| RESORT1 | string | 1 | `GRUJA` |
| MEMBERSHIP_TYPE | string | 1 | `HH` |
| MEMBERSHIP_CARD_NO | string | 1 | `1014545501` |
| MEMBERSHIP_LEVEL | string | 1 | `B`, `D` |
| MEMBERSHIP_TYPE_DESC1 | string | 1 | `HH` |
| MEMBERSHIP_LEVEL_DESC1 | string | 1 | `B`, `D` |

### Nível G_COMMENT_RESV_NAME_ID (comentário da reserva)

| Nó | Tipo estimado | Presença | Exemplos |
|----|----------------|----------|----------|
| RES_COMMENT_ORDER_BY | número | 1 | `2`, `3` |
| **RES_COMMENT_TYPE** | string | 1 | `RES`, `INH` |
| **RES_COMMENT** | string (multilinha) | 1 | `PGMTO DIRETO + EXTRAS`, `TRF R$ 1,684.85 + TXS`, `Motivo: Onboarding RH`, `CST: Quotable Cost : BRL 0.00` |
| RES_COMMENT_DESCRIPTION | string | 1 | `Reservation`, `In-house` |
| COMMENT_RESV_NAME_ID | string | 1 | `1633295` |
| CF_NOTE_DESC | string | 0..1 | `` |

---

## 1.3 Campos chave para auditoria

| Campo | Uso na auditoria |
|-------|-------------------|
| **CONFIRMATION_NO** | Identificador único da reserva no PMS; chave do relatório de saída. |
| **EXTERNAL_REFERENCE** | Referência do canal (formato `NNNNNNNNNN-NNNNNNNNN`); validação de consistência e detecção de canal OTA. |
| **RATE_CODE** | Tarifa; checagem de consistência com MARKET_CODE e tipo de faturamento. |
| **MARKET_CODE** | Mercado/segmento; cruzamento com canal e rate. |
| **GUARANTEE_CODE** | Tipo de garantia (CC=cartão, CO=empresa, CD=depósito, WV=walk-in, 6P=6PM etc.); validação com canal e instrução de pagamento. |
| **COMPANY_NAME** | Faturamento empresa; obrigatório quando COMP_HOUSE ou instrução “faturar empresa”. |
| **ARRIVAL** / **DEPARTURE** | Datas para priorização (ex.: próximas 48h) e cálculo de noites. |
| **ROOM_NO** / **DISP_ROOM_NO** | Atribuição de quarto; vazio = não atribuído. |
| **COUNT_RES_COMMENTS** / **LIST_G_COMMENT_RESV_NAME_ID** | Quantidade e conteúdo de comentários; flags operacionais (PGMTO DIRETO, FATURAR, TRF, etc.). |
| **PAYMENT_METHOD** | MC, CA, VS, AX; consistência com garantia e comentários. |
| **ORIGIN_OF_BOOKING** | TA vs GD; entrada para regras de canal. |
| **COMP_HOUSE** | Indica company house (ex.: `C`); exige COMPANY_NAME e regras de faturamento. |
| **EFFECTIVE_RATE_AMOUNT** / **SHARE_AMOUNT** | Valores para checagem de tarifa zero, divergências e comentários TRF. |
| **EXP_DATE** | Ex.: `XX/XX` = cartão não expirado/ mascarado; vazio pode indicar falta de garantia. |

---

*Documento inferido exclusivamente a partir do XML fornecido. Presença 0..1 = opcional; 1 = sempre presente na amostra.*
