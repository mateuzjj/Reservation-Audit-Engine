# 10. Relatório de observações — Reservation Audit Engine

Resumo das limitações detectadas no XML, ambiguidades, possíveis fontes de erro e impacto na confiança das regras. Baseado exclusivamente no arquivo **res_detail4383227.xml** (Oracle Reports 12.2.1.4.0).

---

## 10.1 Limitações detectadas no XML

### 10.1.1 Ausência de campo explícito de canal

- **Observação:** Não existe elemento que identifique diretamente o canal (Expedia, Booking, Omnibees, direto). Apenas **ORIGIN_OF_BOOKING** (TA, GD) e **EXTERNAL_REFERENCE** (formato NNNNNNNNNN-NNNNNNNNN) estão disponíveis.
- **Impacto:** A classificação de canal depende de um **mapeamento externo** (tabela ou configuração) do primeiro segmento de EXTERNAL_REFERENCE para o nome do canal. Qualquer novo código de fonte exige atualização do mapeamento; sem isso, o canal será "OTA Unknown" ou "Direct" (quando GD).
- **Confiança:** Média; a regra é confiável desde que o mapeamento seja mantido e completo.

### 10.1.2 Formato e significado de EXTERNAL_REFERENCE

- **Observação:** O padrão observado é sempre dois números de 10 e 9 dígitos separados por hífen. Não há documentação no XML sobre o significado (ex.: qual sistema gerou o primeiro número).
- **Impacto:** Interpretação “primeiro = fonte, segundo = reserva” é inferida; se o PMS ou o canal manager usar convenção diferente, a detecção de duplicidade (mesmo EXTERNAL_REFERENCE) ou o mapeamento de canal podem falhar.
- **Confiança:** Média; validar com documentação do PMS/canal manager.

### 10.1.3 COMPANY_NAME com formato livre (C- / T-)

- **Observação:** COMPANY_NAME aparece com padrão "C- ... T- ..." (ex.: "C- Hilton Honors Disc\nT- Tumlare Corporatio"), sugerindo “Company” e “Travel agent”. O formato não é normalizado (quebras de linha, espaços, abreviações).
- **Impacto:** Checagens que dependem de “COMPANY_NAME preenchido” devem tratar string vazia, só espaços e possivelmente “C-”/“T-” sem texto útil. Não é possível, só com o XML, saber se “C-” sem nome é válido ou erro.
- **Confiança:** Alta para “vazio vs não vazio”; baixa para interpretação semântica (qual parte é empresa vs agente) sem regras de parsing adicionais.

### 10.1.4 Comentários em texto livre (RES_COMMENT)

- **Observação:** RES_COMMENT contém instruções operacionais em português e inglês ("PGMTO DIRETO", "FATURAR DIARIAS", "TRF R$", "CST: Quotable Cost : BRL X"). Há variação de grafia ("FATUARAR", "PGTO DIRETO", "FATUARARAR") e de formato de valor.
- **Impacto:** Regras baseadas em palavras-chave podem ter falsos positivos/negativos por sinônimos ou erros de digitação. A extração de valor numérico de "CST: Quotable Cost : BRL X" ou "TRF R$ X" exige parsing frágil (locale, vírgula/ponto).
- **Confiança:** Média; recomenda-se lista configurável de keywords e testes com amostras reais.

### 10.1.5 LIST_G_BILL_RESV sempre vazia na amostra

- **Observação:** Em todo o XML analisado, LIST_G_BILL_RESV aparece sempre vazia (`<LIST_G_BILL_RESV></LIST_G_BILL_RESV>`).
- **Impacto:** Não é possível, com este export, auditar itens de fatura (diárias, extras) por reserva; regras que dependam de “itens faturados” não têm suporte no XML.
- **Confiança:** N/A para regras que dependem de itens de fatura; confiança alta para regras que não dependem.

### 10.1.6 Datas em dois formatos

- **Observação:** ARRIVAL/DEPARTURE em DD/MM/YY (ex.: 02/03/26); TRUNC_BEGIN/TRUNC_END e UPDATE_DATE em DD-MON-YY (ex.: 02-MAR-26). GROUPBY1_SORT_COL em YYYYMMDD (20260302).
- **Impacto:** Cálculo de “dias até chegada” ou comparação de datas exige normalização; inconsistência de formato pode causar erro em parsing ou ordenação.
- **Confiança:** Alta se a implementação normalizar todos os formatos para um único tipo (data); média se houver mais formatos em outros arquivos.

### 10.1.7 GUARANTEE_CODE e SHORT_RESV_STATUS

- **Observação:** Na amostra, GUARANTEE_CODE e SHORT_RESV_STATUS têm os mesmos valores (CC, CO, CD, WV, 6P). Não está documentado no XML se são sempre iguais ou se podem divergir.
- **Impacto:** Regras que usam apenas um dos dois podem perder casos em que o outro difere (se isso ocorrer em outros exports). Não há lista oficial de códigos de garantia no XML.
- **Confiança:** Alta para valores observados; média para novos códigos não vistos na amostra (podem ser válidos ou erro de dado).

### 10.1.8 RATE_CODE e MARKET_CODE sem dicionário

- **Observação:** RATE_CODE e MARKET_CODE são códigos livres (HPPRP1, CIBMS0, BAR, CNR, etc.). Não há elemento no XML que descreva o significado ou a categoria (corporativo, bar, wholesale).
- **Impacto:** A taxonomia e as regras de “divergência rate/market” ou “corporativo” dependem de listas configuráveis mantidas fora do XML. Novos códigos podem não ser classificados ou podem gerar falsos negativos.
- **Confiança:** Média; depende da atualização das listas de rate/market e do alinhamento com o negócio.

### 10.1.9 ROOM_NO e DISP_ROOM_NO

- **Observação:** Em várias reservas ROOM_NO ou DISP_ROOM_NO estão vazios (quarto não atribuído). Não há indicação explícita de “reserva apenas alocação” vs “quarto a atribuir”.
- **Impacto:** A regra “quarto não atribuído em X horas” é confiável para “vazio = não atribuído”; não é possível distinguir “não aplicável” (ex.: bloqueio) sem outro campo ou convenção.
- **Confiança:** Alta para “vazio = não atribuído”; baixa para interpretações adicionais.

### 10.1.10 Typo no nome do elemento

- **Observação:** MOBILE_REGSITERED_YN (typo: “REGSITERED” em vez de “REGISTERED”) aparece no XML.
- **Impacto:** Se alguma regra ou documentação usar o nome correto “REGISTERED”, o mapeamento pode falhar a menos que se aceite o nome real do nó.
- **Confiança:** N/A para auditoria de reservas; apenas cuidado ao referenciar o campo.

---

## 10.2 Ambiguidades

| Tema | Ambiguidade | Efeito nas regras |
|------|-------------|--------------------|
| **TA vs GD** | GD pode ser “Guest Direct” ou “Group Direct”; não há GROUP_ID preenchido na amostra para diferenciar. | Tratar GD como “reserva direta” é seguro; subdividir “grupo” exigiria outro campo. |
| **Tarifa zero** | EFFECTIVE_RATE_AMOUNT=0 pode ser cortesia, pontos, comp, ou erro. | Regras que exigem “justificativa” (comentário ou programa) reduzem falsos positivos mas podem deixar passar erros sem comentário. |
| **Canal “Direct”** | GD sem EXTERNAL_REFERENCE não aparece na amostra; todas as reservas têm EXTERNAL_REFERENCE. | Se no futuro existir TA sem EXTERNAL_REFERENCE, a decisão “Direct” vs “OTA Unknown” deve estar documentada. |
| **Evidência** | O que exatamente incluir em “evidence” (todos os campos da reserva vs só os que dispararam a regra) não está definido no XML. | Definir na especificação do output para consistência e privacidade (ex.: mascarar cartão). |

---

## 10.3 Possíveis fontes de erro

1. **Export parcial ou filtrado:** Se o XML for gerado com filtro (ex.: só chegadas em X dias), regras que dependem de “todas as reservas” (ex.: duplicidade de EXTERNAL_REFERENCE) podem não ver duplicatas em outro arquivo.
2. **Atualização do PMS após o export:** O XML é um snapshot; correções feitas no PMS depois do export não aparecem até o próximo arquivo.
3. **Locale e formato numérico:** Valores como "1.684,85" vs "1684.85" em comentários ou em outros nós podem quebrar parsing numérico se não houver normalização.
4. **Encoding:** O XML declara UTF-8; caracteres especiais em nomes ou comentários devem ser validados para não quebrar o parser ou o CSV de saída.
5. **Tamanho do arquivo:** Arquivo grande (ex.: 139k caracteres na amostra) pode exigir processamento em streaming ou limites de tamanho na API para evitar timeouts ou uso excessivo de memória.

---

## 10.4 Impacto na confiança das regras (resumo)

| Área | Confiança | Condição |
|------|-----------|----------|
| Identificação da reserva (CONFIRMATION_NO, ARRIVAL, DEPARTURE) | Alta | Campos presentes e estáveis. |
| Detecção de COMPANY_NAME vazio / COMP_HOUSE | Alta | Tratando string vazia e só espaços. |
| Detecção de garantia (GUARANTEE_CODE) e cartão | Alta | Para códigos e ausência de CREDIT_CARD_NUMBER quando CC. |
| Canal (Expedia, Booking, Omnibees, Direct) | Média | Depende de mapeamento externo de EXTERNAL_REFERENCE. |
| Rate/Market e taxonomia | Média | Depende de listas configuráveis e alinhamento com negócio. |
| Instruções de pagamento em comentários | Média | Keywords e variações de texto; possível falso positivo/negativo. |
| Duplicidade de EXTERNAL_REFERENCE | Média | Confiável dentro do mesmo arquivo; não entre arquivos. |
| Divergência CST / Quotable Cost | Baixa | Parsing de texto livre e formato de valor frágil. |
| Itens de fatura (LIST_G_BILL_RESV) | N/A | Lista vazia na amostra; regras que dependem disso não têm suporte. |

---

## 10.5 Recomendações para reduzir gaps

1. **Manter mapeamento de canal:** Atualizar periodicamente o mapping primeiro_segmento (EXTERNAL_REFERENCE) → canal com códigos fornecidos pelo PMS ou canal manager.
2. **Dicionário de RATE_CODE e MARKET_CODE:** Manter listas (corporativo, bar, wholesale, etc.) e revisar com revenue/comercial quando surgirem códigos novos.
3. **Normalização de datas e números:** Definir formato canônico (ISO 8601 para datas; número com ponto decimal para valores) na ingestão do XML.
4. **Lista de keywords para comentários:** Parametrizar termos em configuração e incluir variantes (FATUARAR, PGTO DIRETO, etc.); revisar com operação para reduzir falsos positivos.
5. **Documentar convenções do PMS:** Para COMP_HOUSE, GUARANTEE_CODE e formato de COMPANY_NAME, documentar significados oficiais quando disponíveis; isso aumenta a confiança das regras e facilita manutenção.
6. **Revalidação pós-correção:** Sempre que possível, rodar o motor novamente sobre o XML atualizado após correções no PMS para validar que os issues foram resolvidos e que não surgiram novos.

---

*Este relatório reflete apenas o que foi observado no XML fornecido. Qualquer alteração no formato de export do PMS ou na origem dos dados pode exigir revisão do esquema inferido e das regras.*
