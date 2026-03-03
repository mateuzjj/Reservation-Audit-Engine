# 9. Recomendações operacionais — Reservation Audit Engine

Sugestões práticas de priorização de correções e modelo de workflow para operadores, com base nos campos e regras inferidos do XML.

---

## 9.1 Priorização de correções

### Critérios sugeridos (em ordem de prioridade)

1. **Risk score alto e chegada nas próximas 48h**  
   Priorizar reservas com `risk_score` ≥ 70 e data de `ARRIVAL` dentro de 48 horas. Essas reservas têm maior impacto imediato (check-in, cobrança, disputa).

2. **Severidade alta independente da data**  
   Todas as issues de severidade **alta** (ex.: rate_code ausente, fatura empresa sem company_name, COMP_HOUSE sem company, garantia CC sem cartão, duplicidade de external_reference) devem entrar na fila de correção antes das de severidade média/baixa.

3. **Canal OTA com garantia/pagamento inconsistente**  
   Reservas classificadas como OTA (Expedia, Booking, Omnibees) com issues de garantia ou instrução de pagamento incompatível com o canal — alto risco de chargeback ou rejeição pelo canal.

4. **Risk score médio e chegada em 3–7 dias**  
   Em seguida, tratar reservas com `risk_score` entre 40 e 69 e chegada na semana seguinte.

5. **Risk score baixo ou chegada distante**  
   Por último, reservas com `risk_score` < 40 ou chegada além de 7 dias; podem ser tratadas em lote ou na rotina diária.

### Exemplo de ordenação (query/filtro conceitual)

- Ordenar por: `risk_score` DESC, depois `days_until_arrival` ASC.
- Filtrar primeiro: `risk_score >= 70` E `days_until_arrival <= 2`.
- Em seguida: `severity = high` (todas as datas).
- Depois: `risk_score >= 40` E `days_until_arrival <= 7`.

---

## 9.2 Modelo de workflow sugerido para operadores

Fluxo em etapas, do alerta à revalidação.

### Etapa 1 — Alert

- O **Reservation Audit Engine** processa o XML (diariamente ou sob demanda) e gera o relatório com `detected_issues`, `suggested_action`, `risk_score`, `evidence`.
- As reservas com pelo menos um issue (ou com `risk_score` acima de um threshold configurável) são disponibilizadas em lista ou painel para **revisão humana**.

### Etapa 2 — Revisão humana

- Operador abre a reserva no relatório e confere:
  - **evidence**: valores do XML que motivaram o alerta.
  - **suggested_action**: ação recomendada.
- Operador decide:
  - **Corrigir** → segue para Etapa 3.
  - **Falso positivo** → marca como “revisado, sem ação” (e opcionalmente registra motivo para afinamento das regras).
  - **Adiar** → mantém na fila com data de revisão (ex.: próximo dia).

### Etapa 3 — Correção no PMS

- Operador acessa o PMS com o `confirmation_no` e aplica as correções necessárias (ex.: preencher COMPANY_NAME, ajustar garantia, incluir RATE_CODE, atribuir quarto).
- Ao finalizar, marca a reserva como “corrigida” no fluxo de auditoria (pode ser em planilha, sistema de tarefas ou integração com PMS).

### Etapa 4 — Revalidação

- **Opção A:** Na próxima execução do motor (ex.: no dia seguinte), o XML atualizado é processado novamente; a reserva deve sair da lista de issues ou ter `risk_score` reduzido.
- **Opção B:** Se houver API de re-auditoria por reserva, disparar revalidação apenas para os `confirmation_no` corrigidos e conferir se os issues foram resolvidos.

### Etapa 5 — Fechamento e melhoria

- Reservas revalidadas sem issues são arquivadas como “resolvidas”.
- Casos marcados como “falso positivo” podem alimentar ajustes na **configuração de regras** (desativar regra, refinar condição ou parâmetros) para reduzir ruído nas próximas execuções.

---

## 9.3 Papéis sugeridos

| Papel | Responsabilidade |
|------|-------------------|
| **Operador de reservas** | Revisar alertas, corrigir reservas no PMS, marcar como corrigido/falso positivo. |
| **Supervisor** | Priorizar fila (ex.: por risk_score e chegada), validar correções críticas, tratar exceções. |
| **Revenue/Comercial** | Ajustar regras de rate/market e validar casos de tarifa zero ou corporativo. |
| **TI/Engenharia** | Manter motor de auditoria, regras (YAML/JSON), mapeamento de canais e integração com PMS/API. |

---

## 9.4 Frequência sugerida de execução

- **Diária:** processar XML de reservas (exportação noturna do PMS) e gerar relatório pela manhã para revisão no mesmo dia.
- **Sob demanda:** para testes, revalidação após correções ou arquivos adicionais.
- **Pré-check-in (opcional):** para reservas com chegada em 24h, rodar auditoria novamente sobre o subset de reservas do dia e priorizar apenas as que ainda apresentam issues.

---

## 9.5 Métricas recomendadas

- **Volume:** número de reservas com pelo menos um issue por dia; tendência semanal.
- **Prioridade:** quantidade por severidade (alta/média/baixa) e por faixa de risk_score.
- **Resolução:** tempo médio entre alerta e marcação como “corrigido”; % de alertas resolvidos antes do check-in.
- **Falsos positivos:** % de alertas marcados como “revisado, sem ação” para refinar regras.

---

*Estas recomendações permitem que a operação use o relatório do Reservation Audit Engine de forma ordenada e mensurável, sem prescrever a implementação técnica do workflow.*
