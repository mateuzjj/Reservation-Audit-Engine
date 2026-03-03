# 4. Lista de verificações/auditorias — Reservation Audit Engine

Lista exaustiva de checagens a serem aplicadas sobre cada reserva, com severidade (baixa / média / alta) e impacto operacional. Baseada nos campos e padrões observados no XML.

---

## 4.1 Severidade e impacto

- **Alta:** risco de no-show, cobrança indevida, disputa comercial ou falha no check-in se não corrigido antes da chegada.
- **Média:** inconsistência que pode gerar retrabalho, reclamação ou divergência contábil.
- **Baixa:** melhoria de dados ou conformidade; não bloqueia operação.

---

## 4.2 Checagens

| # | Verificação | Condição (linguagem natural) | Severidade | Impacto operacional |
|---|-------------|-------------------------------|------------|----------------------|
| 1 | **rate_code ausente ou vazio** | RATE_CODE nulo, vazio ou somente espaços. | Alta | Tarifa indefinida; risco de cobrança errada ou impossibilidade de faturamento. |
| 2 | **Reserva faturada sem company_name** | Instrução de faturamento empresa (comentário contendo "FATURAR", "FATUARAR", "DIARIAS E TAXAS" para empresa, ou COMP_HOUSE = C) e COMPANY_NAME vazio. | Alta | Cobrança direcionada à empresa sem identificação; disputa e retrabalho. |
| 3 | **OTA com guarantee_code = CASH ou equivalente** | Canal classificado como OTA (Expedia, Booking, Omnibees) e GUARANTEE_CODE indicando garantia incompatível (ex.: CO sem company, ou código que implique pagamento local em dinheiro quando o canal exige cartão). | Alta | Conflito com política do canal; possível rejeição ou chargeback. |
| 4 | **external_reference inconsistente** | ORIGIN_OF_BOOKING = TA e EXTERNAL_REFERENCE vazio; ou formato de EXTERNAL_REFERENCE diferente de NNNNNNNNNN-NNNNNNNNN; ou primeiro segmento não mapeável para nenhum canal conhecido. | Média | Dificulta reconciliação com canal e identificação da fonte; risco de duplicidade ou erro de canal. |
| 5 | **Divergência entre rate_code e market_code** | RATE_CODE e MARKET_CODE semanticamente incompatíveis (ex.: MARKET_CODE = BAR com RATE_CODE corporativo CIBMS0; ou MARKET_CODE = CNR com RATE_CODE de bar HPPRP1) conforme taxonomia definida. | Média | Tarifa ou mercado incorreto no PMS; cobrança ou relatório gerencial errado. |
| 6 | **Falta de garantia** | GUARANTEE_CODE vazio ou valor não reconhecido; ou reserva com status confirmado (SHORT_RESV_STATUS = CC) sem GUARANTEE_CODE válido e sem PAYMENT_METHOD/CREDIT_CARD_NUMBER quando exigido. | Alta | Reserva não garantida; no-show sem cobrança; conflito com política do canal. |
| 7 | **Comentários com flags operacionais sem ação** | RES_COMMENT contém "PGMTO DIRETO", "FATURAR", "TRF", "PAGTO VIA LINK", "DEBITAR" etc., mas PAYMENT_METHOD ou GUARANTEE_CODE ou COMPANY_NAME não condizem com a instrução (ex.: "FATURAR DIARIAS" sem COMPANY_NAME). | Alta/Média | Instrução não refletida no PMS; cobrança ou check-in incorretos. |
| 8 | **company_name ausente em rate corporativo** | RATE_CODE ou MARKET_CODE classificado como corporativo (CMP, CNR, CIBMS0, etc.) e COMPANY_NAME vazio. | Alta | Faturamento empresa sem identificação do pagador. |
| 9 | **COMP_HOUSE = C sem company_name** | COMP_HOUSE = C e COMPANY_NAME vazio. | Alta | Company house sem empresa associada; cobrança e relatório incorretos. |
| 10 | **Tarifa zero sem justificativa** | EFFECTIVE_RATE_AMOUNT = 0 e nenhum de: comentário explicativo (comp, cortesia, pontos), GUARANTEE_CODE CO com COMPANY_NAME, MARKET_CODE CMP com COMP_HOUSE. | Média | Possível erro de tarifa ou rate não aplicado; verificação manual. |
| 11 | **Cartão mascarado (XX/XX) com garantia por cartão** | EXP_DATE = "XX/XX" e GUARANTEE_CODE = CC; cartão não validável para cobrança. | Média | Risco de charge falho no check-in ou no pós-estadia. |
| 12 | **CREDIT_CARD_NUMBER ausente com guarantee CC** | GUARANTEE_CODE = CC e CREDIT_CARD_NUMBER vazio. | Alta | Garantia por cartão sem número; impossível cobrança. |
| 13 | **Reserva OTA sem external_reference** | Canal = OTA (por ORIGIN_OF_BOOKING + mapeamento) e EXTERNAL_REFERENCE vazio. | Média | Não permite conciliação com extranet do canal. |
| 14 | **COUNT_RES_COMMENTS = 0 e canal OTA** | Reserva identificada como OTA e COUNT_RES_COMMENTS = 0 (sem comentários de instrução de pagamento/canal). | Baixa | Pode indicar comentário não migrado ou reserva incompleta; revisão opcional. |
| 15 | **ROOM_NO vazio em reserva confirmada próxima** | SHORT_RESV_STATUS = CC, ARRIVAL em até 24–48h e ROOM_NO/DISP_ROOM_NO vazio. | Média | Quarto não atribuído; impacto em alocação e experiência. |
| 16 | **Duplicidade de external_reference** | Mesmo EXTERNAL_REFERENCE em mais de uma reserva (mesmo CONFIRMATION_NO ou diferentes). | Alta | Duplicidade de reserva ou erro de integração. |
| 17 | **PAYMENT_METHOD incompatível com garantia** | GUARANTEE_CODE = CO (company) e PAYMENT_METHOD = cartão (MC, VS, AX) sem COMPANY_NAME; ou GUARANTEE_CODE = CC e PAYMENT_METHOD = CA (cash) sem política que permita. | Média | Instrução de pagamento ambígua ou incorreta. |
| 18 | **Comentário "CST: Quotable Cost" com valor divergente** | RES_COMMENT contém "CST: Quotable Cost : BRL X" e EFFECTIVE_RATE_AMOUNT/SHARE_AMOUNT diverge além do threshold configurável. | Média | Possível divergência tarifária canal vs PMS. |
| 19 | **market_code ausente ou inválido** | MARKET_CODE vazio ou valor não pertencente à lista conhecida (BAR, CMP, CNR, CONS, DISC, IT, LNR, MKT, etc.). | Média | Relatórios e regras de rate/market inconsistentes. |
| 20 | **ARRIVAL ou DEPARTURE inválidas** | Data de chegada ou partida em formato inesperado ou DEPARTURE &lt; ARRIVAL. | Alta | Cálculo de noites e disponibilidade incorretos. |
| 21 | **Guarantee WV (walk-in) com ORIGIN = TA** | GUARANTEE_CODE = WV e ORIGIN_OF_BOOKING = TA. | Baixa | Possível inconsistência (walk-in normalmente direto). |
| 22 | **Múltiplos comentários "TRF" com valores diferentes** | Mais de um RES_COMMENT com "TRF R$" e valores numéricos distintos para a mesma reserva. | Média | Instrução de transferência ambígua; risco de valor errado. |
| 23 | **BILL_TO_ADDRESS preenchido sem company_name** | BILL_TO_ADDRESS não vazio e COMPANY_NAME vazio em reserva com instrução de faturar empresa. | Baixa | Endereço de cobrança sem identificação da empresa. |
| 24 | **EFFECTIVE_RATE_AMOUNT ≠ SHARE_AMOUNT** | Valores diferentes sem regra de negócio que justifique (ex.: compartilhamento de quarto). | Média | Possível erro de rate ou de repasse. |
| 25 | **LIST_G_BILL_RESV presente com instrução "pagamento direto"** | Lista de itens de fatura (LIST_G_BILL_RESV não vazia) e comentário indicando pagamento direto ao hóspede. | Baixa | Verificar se fatura é para extras ou diárias; consistência. |

---

## 4.3 Resumo por severidade

- **Alta:** 1, 2, 3, 6, 7 (quando fatura empresa), 8, 9, 12, 16, 20.
- **Média:** 4, 5, 7 (outros casos), 10, 11, 13, 15, 17, 18, 19, 22, 24.
- **Baixa:** 14, 21, 23, 25.

---

*Cada checagem deve ser parametrizável (ativar/desativar, thresholds, listas de códigos) via configuração de regras.*
