# 5. Output esperado — Reservation Audit Engine

Formato do relatório tabular de auditoria e exemplo com 10 linhas baseadas em casos típicos extraídos do XML.

---

## 5.1 Colunas mínimas do relatório

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| **confirmation_no** | string | Número de confirmação da reserva (CONFIRMATION_NO). |
| **guest_name** | string | Nome do hóspede (FULL_NAME ou FULL_NAME_NO_SHR_IND). |
| **channel** | string | Canal detectado: Expedia Group, Booking.com, Omnibees, Direct, Unknown. |
| **rate_code** | string | Código de tarifa (RATE_CODE). |
| **market_code** | string | Código de mercado (MARKET_CODE). |
| **detected_issues** | lista/array | Lista de códigos ou descrições curtas dos problemas detectados (ex.: RATE_MARKET_MISMATCH, MISSING_COMPANY_NAME). |
| **suggested_action** | string | Texto curto com ação sugerida para o operador. |
| **risk_score** | número 0–100 | Pontuação de risco agregada (0 = sem issues, 100 = crítico). |
| **evidence** | string ou objeto | Valores do XML que justificam o alerta (ex.: trechos de campos ou JSON com campos relevantes). |

---

## 5.2 Exemplo em CSV (cabecalho + 10 linhas)

```csv
confirmation_no,guest_name,channel,rate_code,market_code,detected_issues,suggested_action,risk_score,evidence
1553114,Canclini Julie Helene Lucie,OTA (TA),HPPRP1,BAR,"INSTRUCTION_PAYMENT_DIRECT_NO_BILLING","Verificar se faturamento está como empresa ou direto; conferir COMPANY_NAME.",35,"RES_COMMENT=PGMTO DIRETO + EXTRAS; COMPANY_NAME=C- Hilton Honors Disc T- Tumlare Corporatio"
1553333,Luz Amanda Miss,Direct,CMP,CMP,"MISSING_COMPANY_NAME; COMP_HOUSE_NO_COMPANY","Incluir COMPANY_NAME para reserva company house (COMP_HOUSE=C).",85,"COMP_HOUSE=C; COMPANY_NAME=vazio; GUARANTEE_CODE=CO"
1553408,Barleben Erik Sebastian,OTA (TA),FW,CNR,"RATE_MARKET_MISMATCH; INSTRUCTION_PAYMENT_DIRECT","Conferir rate FW com mercado CNR; validar instrução PGMTO DIRETO com canal.",45,"RATE_CODE=FW; MARKET_CODE=CNR; RES_COMMENT=PGMTO DIRETO + EXTRAS"
1552027,Costa Fraga Paraguassu Gustavo,OTA (TA),CIBMS0,CNR,"","Nenhuma ação necessária.",5,"COMPANY_NAME preenchido; GUARANTEE_CODE=CC; comentário PGMTO DIRETO consistente"
1551677,Dos Santos Saragiotto Renato,OTA (TA),CIBMS0,CNR,"ROOM_NOT_ASSIGNED","Atribuir quarto antes do check-in (ROOM_NO vazio).",25,"ROOM_NO=vazio; DISP_ROOM_NO=vazio; ARRIVAL=02/03/26"
1549829,Hanlon Fiona Mrs,Direct,TCSBI2,CONS,"","Nenhuma ação necessária.",0,"ORIGIN=GD; COMPANY_NAME preenchido; GUARANTEE_CODE=CC"
1547496,Lacerda Charles,OTA (TA),HHNSRR,DISC,"MISSING_COMPANY_NAME; ZERO_RATE","Reserva DISC com tarifa 0 e COMPANY_NAME vazio; verificar se é pontos/cortesia e se empresa deve constar.",40,"EFFECTIVE_RATE_AMOUNT=0; COMPANY_NAME=vazio; MARKET_CODE=DISC"
1633559,Luz Amanda Miss,Direct,CMP,CMP,"COMP_HOUSE_NO_COMPANY; ZERO_RATE","Incluir COMPANY_NAME; confirmar se tarifa zero é intencional (comp/cortesia).",75,"COMP_HOUSE=C; COMPANY_NAME=vazio; SHARE_AMOUNT=0"
1553408,Barleben Erik Sebastian,OTA (TA),FW,CNR,"INSTRUCTION_PAYMENT_DIRECT","Validar instrução de pagamento direto com canal OTA.",30,"RES_COMMENT=PGMTO DIRETO + EXTRAS; TRF R$ 1487.70 + TXS"
1553333,Luz Amanda Miss,Direct,CMP,CMP,"MISSING_COMPANY_NAME; COMP_HOUSE=C","Obrigatório preencher COMPANY_NAME para company house.",85,"COMPANY_NAME=vazio; COMP_HOUSE=C; GUARANTEE_CODE=CO"
```

---

## 5.3 Exemplo em JSON (estrutura e 2 registros)

```json
{
  "audit_run_id": "20260302-001",
  "source_file": "res_detail4383227.xml",
  "generated_at": "2026-03-02T10:00:00Z",
  "total_reservations": 25,
  "reservations_with_issues": 10,
  "records": [
    {
      "confirmation_no": "1553114",
      "guest_name": "Canclini,Julie Helene Lucie",
      "channel": "OTA (TA)",
      "rate_code": "HPPRP1",
      "market_code": "BAR",
      "detected_issues": ["INSTRUCTION_PAYMENT_DIRECT_NO_BILLING"],
      "suggested_action": "Verificar se faturamento está como empresa ou direto; conferir COMPANY_NAME.",
      "risk_score": 35,
      "evidence": {
        "RES_COMMENT": "PGMTO DIRETO +  EXTRAS",
        "COMPANY_NAME": "C- Hilton Honors Disc T- Tumlare Corporatio",
        "GUARANTEE_CODE": "CC"
      }
    },
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
        "GUARANTEE_CODE": "CO",
        "SHARE_AMOUNT": "0"
      }
    }
  ]
}
```

---

## 5.4 Origem das 10 linhas de exemplo (referência ao XML)

| confirmation_no | Origem no XML |
|-----------------|----------------|
| 1553114 | Primeira reserva; TA; BAR/HPPRP1; comentário PGMTO DIRETO + EXTRAS. |
| 1553333 | GD; CMP/CMP; COMP_HOUSE=C; COMPANY_NAME vazio; CO. |
| 1553408 | TA; CNR/FW; comentário PGMTO DIRETO; company Banco Santander/World Travel. |
| 1552027 | TA; CNR/CIBMS0; COMPANY_NAME I B M / Flytour; PGMTO DIRETO. |
| 1551677 | TA; ROOM_NO vazio; CIBMS0/CNR. |
| 1549829 | GD; CONS/TCSBI2; Hanlon; company Hilton Value / Travel Incorporate. |
| 1547496 | TA; DISC/HHNSRR; EFFECTIVE_RATE_AMOUNT=0; COMPANY_NAME vazio. |
| 1633559 | Mesmo hóspede 1553333 (Luz, Amanda); CMP; COMP_HOUSE=C; COMPANY_NAME vazio. |
| (1553408 repetido) | Mesmo caso Barleben; foco em instrução pagamento. |
| (1553333 repetido) | Mesmo caso Luz; foco COMPANY_NAME + COMP_HOUSE. |

As 10 linhas cobrem: OTA com instrução pagamento, direta sem company, rate/market mismatch, company house sem empresa, quarto não atribuído, tarifa zero sem company, e reservas sem issues (risco baixo ou zero).

---

*O relatório final deve ser gerado apenas para reservas com detected_issues não vazio e/ou risk_score acima de um threshold configurável; opcionalmente incluir todas as reservas com risk_score 0 para auditoria completa.*
