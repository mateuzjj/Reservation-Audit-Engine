# 2. Classificação de canais — Reservation Audit Engine

Regras deduzidas a partir do XML para identificar canais. O XML **não contém** um campo explícito de “canal” ou “fonte”; a classificação baseia-se em **ORIGIN_OF_BOOKING**, **EXTERNAL_REFERENCE** e padrões de **COMPANY_NAME** / comentários quando disponíveis.

---

## 2.1 Categorias consideradas

- **Expedia Group** (Expedia, Hotels.com, etc.)
- **Booking.com**
- **Omnibees** (PMS/Channel Manager típico em operações brasileiras)
- **Reservas diretas** (hotel site, central de reservas, walk-in)

---

## 2.2 Evidências no XML

### ORIGIN_OF_BOOKING

- Valores observados: **TA**, **GD**.
- **TA** = Travel Agent (intermediário/OTA ou agência).
- **GD** = Group Direct ou Guest Direct (reserva direta ou grupo).

Exemplos no XML:

```xml
<ORIGIN_OF_BOOKING>TA</ORIGIN_OF_BOOKING>
<ORIGIN_OF_BOOKING>GD</ORIGIN_OF_BOOKING>
```

### EXTERNAL_REFERENCE

- Formato observado: `NNNNNNNNNN-NNNNNNNNN` (dois segmentos numéricos separados por hífen).
- Exemplos: `3431187369-425194957`, `3424811981-425906982`, `3429401303-426516908`.

Interpretação típica em PMS/Channel Manager:

- Primeiro segmento: identificador da **fonte/canal** no sistema externo.
- Segundo segmento: identificador da **reserva** na fonte.

Para classificar canal, é necessário um **mapeamento externo** (tabela ou configuração) do primeiro segmento para o nome do canal. No XML em si não há rótulo de canal; apenas o par (ORIGIN_OF_BOOKING, external_reference) está disponível.

---

## 2.3 Regras deduzidas para cada canal

### Expedia Group

| Regra | Condição (linguagem natural) | Padrões no XML que sustentam |
|-------|-----------------------------|------------------------------|
| E1 | ORIGIN_OF_BOOKING = TA e EXTERNAL_REFERENCE presente e primeiro segmento pertencer à lista de códigos Expedia (configurável). | `<ORIGIN_OF_BOOKING>TA</ORIGIN_OF_BOOKING>` + `<EXTERNAL_REFERENCE>3431187369-425194957</EXTERNAL_REFERENCE>`. O valor `3431187369` (exemplo) seria mapeado para Expedia na configuração. |
| E2 | COMPANY_NAME ou comentário RES contiver substring “Expedia”, “Hotels.com”, “EAN” ou equivalente (quando preenchido). | Ex.: `<COMPANY_NAME>C- Expedia ...</COMPANY_NAME>` ou `<RES_COMMENT>...Expedia...</RES_COMMENT>`. No XML de exemplo não aparece; regra para quando houver dados. |

**Exemplo de trecho XML coerente com canal OTA (classificação posterior por mapping):**

```xml
<ORIGIN_OF_BOOKING>TA</ORIGIN_OF_BOOKING>
<EXTERNAL_REFERENCE>3431187369-425194957</EXTERNAL_REFERENCE>
<MARKET_CODE>BAR</MARKET_CODE>
<RATE_CODE>HPPRP1</RATE_CODE>
```

---

### Booking.com

| Regra | Condição (linguagem natural) | Padrões no XML que sustentam |
|-------|-----------------------------|------------------------------|
| B1 | ORIGIN_OF_BOOKING = TA e EXTERNAL_REFERENCE presente e primeiro segmento pertencer à lista de códigos Booking (configurável). | Mesmo padrão que E1; distinção apenas pelo mapeamento do primeiro segmento de EXTERNAL_REFERENCE (ex.: `3424811981` → Booking.com). |
| B2 | COMPANY_NAME ou comentário RES contiver “Booking”, “Booking.com” ou “Priceline” (quando preenchido). | Ex.: `<RES_COMMENT>Booking.com ID: 123</RES_COMMENT>`. Não observado no arquivo; regra para enriquecimento. |

**Exemplo de trecho XML (classificação por mapping do primeiro segmento):**

```xml
<ORIGIN_OF_BOOKING>TA</ORIGIN_OF_BOOKING>
<EXTERNAL_REFERENCE>3424811981-425906982</EXTERNAL_REFERENCE>
```

---

### Omnibees

| Regra | Condição (linguagem natural) | Padrões no XML que sustentam |
|-------|-----------------------------|------------------------------|
| O1 | ORIGIN_OF_BOOKING = TA e EXTERNAL_REFERENCE com primeiro segmento mapeado como Omnibees na configuração. | Formato idêntico aos demais; identificação apenas por tabela de mapeamento (ex.: primeiro segmento em faixa específica ou lista de IDs). |
| O2 | Comentário ou COMPANY_NAME mencionar “Omnibees”, “BEES”, “Channel Manager” (quando existir). | Ex.: `<RES_COMMENT>Omnibees ref: xxx</RES_COMMENT>`. Não presente no XML analisado. |

**Exemplo:** mesma estrutura que outros TA; canal definido por configuração do primeiro segmento de EXTERNAL_REFERENCE.

---

### Reservas diretas

| Regra | Condição (linguagem natural) | Padrões no XML que sustentam |
|-------|-----------------------------|------------------------------|
| D1 | ORIGIN_OF_BOOKING = GD. | `<ORIGIN_OF_BOOKING>GD</ORIGIN_OF_BOOKING>`. Ex.: reservas 1553333 (CMP/comp), 1549829 (TCSBI2/CONS), WH2 (IT), L9 (LNR), PGBB01 (MKT). |
| D2 | ORIGIN_OF_BOOKING = TA com EXTERNAL_REFERENCE vazio ou ausente. | No XML analisado todas as reservas TA têm EXTERNAL_REFERENCE preenchido; regra para casos em que existir TA sem referência. |
| D3 | GUARANTEE_CODE = WV (walk-in). | `<GUARANTEE_CODE>WV</GUARANTEE_CODE>` + `<SHORT_RESV_STATUS>WV</SHORT_RESV_STATUS>`. Indica chegada direta. |

**Exemplos no XML (GD = direta):**

```xml
<ORIGIN_OF_BOOKING>GD</ORIGIN_OF_BOOKING>
<CONFIRMATION_NO>1553333</CONFIRMATION_NO>
<MARKET_CODE>CMP</MARKET_CODE>
<RATE_CODE>CMP</RATE_CODE>
<GUARANTEE_CODE>CO</GUARANTEE_CODE>
<COMP_HOUSE>C</COMP_HOUSE>
```

```xml
<ORIGIN_OF_BOOKING>GD</ORIGIN_OF_BOOKING>
<EXTERNAL_REFERENCE>3424361019-425756200</EXTERNAL_REFERENCE>
<MARKET_CODE>IT</MARKET_CODE>
<RATE_CODE>WH2</RATE_CODE>
<GUARANTEE_CODE>WV</GUARANTEE_CODE>
```

---

## 2.4 Resumo e uso

- **Canal explícito não existe no XML;** apenas ORIGIN_OF_BOOKING, EXTERNAL_REFERENCE e eventualmente COMPANY_NAME/RES_COMMENT.
- **GD** → tratar como reserva direta (ou grupo direto), salvo regra de negócio contrária.
- **TA** + EXTERNAL_REFERENCE → canal determinado por **mapeamento configurável** do primeiro segmento (ex.: 3431187369 → Expedia Group, 3424811981 → Booking.com, faixas → Omnibees).
- **TA** sem EXTERNAL_REFERENCE → classificar como direta ou “canal desconhecido” conforme política.
- Nomes em COMPANY_NAME ou texto em RES_COMMENT podem **refinar** a classificação quando disponíveis (ex.: “Expedia”, “Booking”, “Omnibees”).

A implementação deve usar um **arquivo de configuração** (ex.: JSON/YAML) com o mapping primeiro_segmento_external_reference → canal (Expedia Group, Booking.com, Omnibees, Direct) para produzir o campo `channel` no relatório de auditoria.
