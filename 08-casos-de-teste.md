# 8. Casos de teste e validação — Reservation Audit Engine

Casos essenciais (unitários e de integração) com descrição do input (trecho XML), comportamento esperado e critérios de aceitação. Inclui casos de borda e exemplos de falsos positivos/negativos conhecidos.

---

## 8.1 Testes unitários (por regra/checagem)

### U01 — rate_code ausente

| Item | Descrição |
|------|------------|
| **Input** | Trecho XML de uma reserva com `<RATE_CODE></RATE_CODE>` ou elemento RATE_CODE ausente. |
| **Comportamento esperado** | A reserva é sinalizada com issue `rate_code_ausente` (R001); risk_score incrementado conforme severidade alta. |
| **Critério de aceitação** | detected_issues contém o código da regra; suggested_action não vazio; evidence inclui o campo RATE_CODE (vazio ou ausente). |
| **Caso de borda** | RATE_CODE com apenas espaços em branco → deve ser tratado como ausente. |

---

### U02 — COMPANY_NAME vazio com COMP_HOUSE = C

| Item | Descrição |
|------|------------|
| **Input** | `<COMP_HOUSE>C</COMP_HOUSE>` e `<COMPANY_NAME></COMPANY_NAME>`. |
| **Comportamento esperado** | Issue `comp_house_sem_company` (R009); severidade alta. |
| **Critério de aceitação** | suggested_action indica preenchimento de COMPANY_NAME; evidence contém COMP_HOUSE e COMPANY_NAME. |
| **Falso negativo conhecido** | Se a regra exigir apenas COMP_HOUSE=C e não considerar COMPANY_NAME com espaços → normalizar string vazia/whitespace como vazio. |

---

### U03 — Comentário "PGMTO DIRETO" sem inconsistência

| Item | Descrição |
|------|------------|
| **Input** | Reserva com `<RES_COMMENT>PGMTO DIRETO + EXTRAS</RES_COMMENT>`, GUARANTEE_CODE=CC, PAYMENT_METHOD=MC, COMPANY_NAME preenchido (quando aplicável). |
| **Comportamento esperado** | Não deve gerar issue de "instrução inconsistente" se a combinação garantia/pagamento/empresa for coerente. |
| **Critério de aceitação** | Nenhum issue R007 para esta reserva, ou evidência de que a regra não dispara quando dados estão alinhados. |
| **Falso positivo conhecido** | Se a regra considerar qualquer comentário "PGMTO DIRETO" como inconsistente sem checar COMPANY_NAME → ajustar condição para só alertar quando faltar empresa onde necessário. |

---

### U04 — EXTERNAL_REFERENCE formato inválido

| Item | Descrição |
|------|------------|
| **Input** | `<ORIGIN_OF_BOOKING>TA</ORIGIN_OF_BOOKING>` e `<EXTERNAL_REFERENCE>ABC-123</EXTERNAL_REFERENCE>` (não segue NNNNNNNNNN-NNNNNNNNN). |
| **Comportamento esperado** | Issue `external_reference_inconsistente` (R004). |
| **Critério de aceitação** | evidence inclui o valor de EXTERNAL_REFERENCE; mensagem indica formato esperado. |
| **Borda** | EXTERNAL_REFERENCE com 10 dígitos-9 dígitos mas com hífen diferente (ex.: espaço) → definir se normalização é feita (trim, substituição) antes da validação. |

---

### U05 — Tarifa zero com justificativa (DISC / pontos)

| Item | Descrição |
|------|------------|
| **Input** | `<EFFECTIVE_RATE_AMOUNT>0</EFFECTIVE_RATE_AMOUNT>`, `<MARKET_CODE>DISC</MARKET_CODE>`, `<RATE_CODE>HHNSRR</RATE_CODE>`, comentário contendo "reward" ou "pontos". |
| **Comportamento esperado** | Não deve gerar issue `tarifa_zero_sem_justificativa` (R010). |
| **Critério de aceitação** | Reserva não listada para R010 ou risk_score não incrementado por essa regra. |
| **Falso positivo** | Tarifa zero com COMPANY_NAME vazio mas programa de fidelidade (HH) → pode ser aceitável; regra deve considerar MEMBERSHIP_TYPE ou comentário. |

---

### U06 — Duplicidade de EXTERNAL_REFERENCE

| Item | Descrição |
|------|------------|
| **Input** | Dois blocos G_RESERVATION no mesmo XML com mesmo EXTERNAL_REFERENCE e CONFIRMATION_NO diferentes. |
| **Comportamento esperado** | Ambas as reservas sinalizadas com issue `duplicidade_external_reference` (R014). |
| **Critério de aceitação** | Ambas aparecem no relatório com o mesmo issue; evidence pode incluir o outro confirmation_no. |

---

### U07 — RATE_CODE e MARKET_CODE compatíveis (BAR + HPPRP1)

| Item | Descrição |
|------|------------|
| **Input** | `<MARKET_CODE>BAR</MARKET_CODE>` e `<RATE_CODE>HPPRP1</RATE_CODE>`. |
| **Comportamento esperado** | Não deve gerar issue de divergência rate/market (R005). |
| **Critério de aceitação** | Nenhum R005 para esta reserva. |

---

### U08 — RATE_CODE corporativo sem COMPANY_NAME

| Item | Descrição |
|------|------------|
| **Input** | `<RATE_CODE>CIBMS0</RATE_CODE>`, `<MARKET_CODE>CNR</MARKET_CODE>`, `<COMPANY_NAME></COMPANY_NAME>`. |
| **Comportamento esperado** | Issue `corporativo_sem_company_name` (R008); severidade alta. |
| **Critério de aceitação** | detected_issues inclui o código da regra; evidence contém RATE_CODE, MARKET_CODE, COMPANY_NAME. |

---

## 8.2 Testes de integração

### I01 — XML completo válido (múltiplas reservas)

| Item | Descrição |
|------|------------|
| **Input** | Arquivo XML completo no formato do res_detail4383227.xml (estrutura RES_DETAIL > LIST_G_GROUP_BY1 > G_GROUP_BY1 > LIST_G_RESERVATION > G_RESERVATION). |
| **Comportamento esperado** | API retorna 200; corpo JSON com audit_run_id, total_reservations, reservations_with_issues, records (array); cada registro com confirmation_no, channel, detected_issues, risk_score. |
| **Critério de aceitação** | Número de total_reservations igual à quantidade de G_RESERVATION no XML; records com pelo menos as reservas que violam regras habilitadas; risk_score entre 0 e 100. |

---

### I02 — XML sem RES_DETAIL

| Item | Descrição |
|------|------------|
| **Input** | Corpo XML válido mas root diferente (ex.: `<ROOT><DATA/></ROOT>`). |
| **Comportamento esperado** | Resposta 422 Unprocessable Entity; code UNRECOGNIZED_STRUCTURE; message indicando que nenhuma reserva foi encontrada. |
| **Critério de aceitação** | HTTP 422; body JSON com code e message. |

---

### I03 — Arquivo não XML (binário ou texto)

| Item | Descrição |
|------|------------|
| **Input** | Multipart com arquivo .pdf ou .txt (não XML). |
| **Comportamento esperado** | Resposta 400 Bad Request; code INVALID_INPUT. |
| **Critério de aceitação** | HTTP 400; mensagem indicando que o arquivo não é XML válido. |

---

### I04 — XML malformado (tag não fechada)

| Item | Descrição |
|------|------------|
| **Input** | Conteúdo que não é XML bem-formado (ex.: `<RES_DETAIL><G_RESERVATION></RES_DETAIL>` com LIST_G_GROUP_BY1 ausente ou tag quebrada). |
| **Comportamento esperado** | Resposta 400; code INVALID_INPUT. |
| **Critério de aceitação** | HTTP 400; parser deve rejeitar antes de aplicar regras. |

---

### I05 — Query min_risk_score

| Item | Descrição |
|------|------------|
| **Input** | Mesmo XML válido; request com query `min_risk_score=50`. |
| **Comportamento esperado** | records contém apenas reservas com risk_score >= 50. |
| **Critério de aceitação** | Para todo item em records, risk_score >= 50; total_reservations pode ser o total original, reservations_with_issues pode ser o count filtrado ou total com issues (definir contrato). |

---

### I06 — Formato CSV

| Item | Descrição |
|------|------------|
| **Input** | Request com Accept: text/csv ou format=csv. |
| **Comportamento esperado** | Resposta 200; Content-Type text/csv; primeira linha = cabeçalho; linhas seguintes = uma por reserva (conforme filtros). |
| **Critério de aceitação** | CSV parseável; colunas conforme especificação (confirmation_no, guest_name, channel, rate_code, market_code, detected_issues, suggested_action, risk_score, evidence). |

---

## 8.3 Casos de borda

### B01 — LIST_G_RESERVATION vazia

| Item | Descrição |
|------|------------|
| **Input** | `<RES_DETAIL><LIST_G_GROUP_BY1><G_GROUP_BY1><LIST_G_RESERVATION></LIST_G_RESERVATION></G_GROUP_BY1></LIST_G_GROUP_BY1></RES_DETAIL>`. |
| **Comportamento esperado** | 200 com total_reservations=0, records=[] (ou 422 se definido que “nenhuma reserva” é erro). |
| **Critério de aceitação** | Não 500; resposta consistente com contrato (zero reservas). |

---

### B02 — Campos opcionais ausentes (ROOM_NO, CREDIT_CARD_NUMBER)

| Item | Descrição |
|------|------------|
| **Input** | Reserva com GUARANTEE_CODE=CC e sem elemento CREDIT_CARD_NUMBER (ou vazio). |
| **Comportamento esperado** | Issue R011 (cc_sem_numero_cartao). |
| **Critério de aceitação** | Regra não depende de elemento “ausente” vs “presente e vazio”; ambos tratados como falta de cartão. |

---

### B03 — COMPANY_NAME multilinha com quebras de linha

| Item | Descrição |
|------|------------|
| **Input** | `<COMPANY_NAME>C- Hilton Honors Disc\nT- Tumlare Corporatio</COMPANY_NAME>`. |
| **Comportamento esperado** | Valor normalizado (trim, colapso de espaços) para checagem “vazio”; não considerado vazio; canal/regras que usam COMPANY_NAME devem tratar texto multilinha. |
| **Critério de aceitação** | Não gera R002/R009 por COMPANY_NAME “vazio”; evidência pode exibir valor truncado ou sanitizado. |

---

### B04 — ARRIVAL/DEPARTURE em formatos diferentes

| Item | Descrição |
|------|------------|
| **Input** | `<ARRIVAL>02/03/26</ARRIVAL>` vs `<ARRIVAL>2026-03-02</ARRIVAL>`. XML do Oracle usa DD/MM/YY. |
| **Comportamento esperado** | Parser normaliza ou aceita formato do XML; regra “quarto não atribuído em X horas” usa ARRIVAL corretamente. |
| **Critério de aceitação** | Datas interpretadas sem erro; comparação com “agora” para horas até chegada correta. |

---

## 8.4 Falsos positivos e negativos conhecidos

| Cenário | Tipo | Descrição | Mitigação sugerida |
|---------|------|-----------|---------------------|
| Reserva GD com COMPANY_NAME vazio mas sem instrução de faturar empresa | Falso positivo | R002 pode disparar se keyword “FATURAR” aparecer em outro contexto no comentário. | Restringir R002 a: (COMP_HOUSE=C) OU (comentário com frase explícita “FATURAR DIARIAS”/“FATUARAR” para empresa). |
| Tarifa zero por programa de fidelidade (HH) sem palavra “reward” no comentário | Falso positivo | R010 pode sinalizar. | Considerar LIST_G_MEM_TYPE_LEVEL (HH) como justificativa para tarifa zero quando MARKET_CODE=DISC. |
| Canal “OTA Unknown” para TA com EXTERNAL_REFERENCE novo (primeiro segmento não mapeado) | Comportamento esperado | Não é falso negativo; canal desconhecido é aceitável. | Documentar que mapeamento deve ser atualizado com novos códigos de canal. |
| GUARANTEE_CODE=CO com COMPANY_NAME preenchido mas PAYMENT_METHOD=MC | Inconsistência real | Pode ser empresa que paga com cartão corporativo; não necessariamente erro. | Severidade média; suggested_action = “Conferir se pagamento é empresa ou cartão”. |

---

*Estes casos devem ser automatizados (testes unitários por regra, testes de integração contra API) e revisados quando novas regras ou formatos de XML forem adicionados.*
