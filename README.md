# Reservation Audit Engine — Artefatos e especificações

Produto analítico que, a partir do XML de reservas (formato RES_DETAIL / Oracle Reports), identifica reservas que precisam de ajuste operacional ou comercial antes do check-in.

**Fonte dos artefatos:** inferência exclusiva a partir do arquivo `res_detail4383227.xml` no workspace.

---

## Índice dos entregáveis

| # | Entregável | Arquivo |
|---|------------|---------|
| 1 | Esquema inferido — mapeamento de todos os campos detectados no XML, tipos, presença e campos chave para auditoria | [01-esquema-inferido.md](01-esquema-inferido.md) |
| 2 | Classificação de canais — regras para Expedia Group, Booking.com, Omnibees e reservas diretas; padrões no XML | [02-classificacao-canais.md](02-classificacao-canais.md) |
| 3 | Taxonomia de rate codes — categorias, indicadores e regras de consistência (sem implementação) | [03-taxonomia-rate-codes.md](03-taxonomia-rate-codes.md) |
| 4 | Lista de verificações/auditorias — checagens exaustivas com severidade e impacto operacional | [04-lista-verificacoes-auditorias.md](04-lista-verificacoes-auditorias.md) |
| 5 | Output esperado — colunas do relatório, exemplo CSV/JSON e 10 linhas de exemplo | [05-output-esperado.md](05-output-esperado.md), [exemplo-relatorio-auditoria.csv](exemplo-relatorio-auditoria.csv) |
| 6 | Configuração de regras — template declarativo (YAML/JSON) com regras parametrizáveis | [06-configuracao-regras.yaml](06-configuracao-regras.yaml), [06-configuracao-regras.json](06-configuracao-regras.json) |
| 7 | Contratos e integração — API OpenAPI minimal e esboço de payloads | [07-api-openapi.yaml](07-api-openapi.yaml), [07-payloads-integracao.md](07-payloads-integracao.md) |
| 8 | Casos de teste e validação — unitários, integração, borda e falsos positivos/negativos | [08-casos-de-teste.md](08-casos-de-teste.md) |
| 9 | Recomendações operacionais — priorização de correções e workflow sugerido | [09-recomendacoes-operacionais.md](09-recomendacoes-operacionais.md) |
| 10 | Relatório de observações — limitações do XML, ambiguidades e impacto na confiança das regras | [10-relatorio-observacoes.md](10-relatorio-observacoes.md) |

---

## Uso pelo time de engenharia

- **Esquema e campos:** use o documento 01 para mapear nós XML → modelo interno e para identificar campos obrigatórios/opcionais.
- **Canais e rate codes:** use 02 e 03 para implementar classificação de canal e validações de consistência rate/market.
- **Regras de auditoria:** use 04 como lista de checagens e 06 (YAML/JSON) como base da engine de regras configurável.
- **API e integração:** use 07 (OpenAPI + payloads) para implementar o endpoint que recebe XML e retorna o relatório.
- **Qualidade:** use 08 para automatizar testes; use 09 e 10 para operação e para refinar regras/parâmetros.

Nenhum desses artefatos prescreve a implementação em código; apenas especificam formato, conteúdo e comportamento esperado.
Deploy no Render

Configuração do serviço

Runtime

* Python

Root Directory

Deixe em branco (não configure app como Root Directory).

Build Command

pip install -r app/requirements.txt

Start Command

cd app && gunicorn --bind 0.0.0.0:$PORT app:app

Motivo da configuração

O projeto possui a seguinte estrutura:

Reservation-Audit-Engine/
├── app/
│   ├── app.py
│   ├── audit_engine.py
│   ├── requirements.txt
│   └── templates/
└── ...

Como o arquivo Flask (app.py) está dentro da pasta app, o Gunicorn precisa ser iniciado a partir desse diretório.

Utilizar Root Directory = app juntamente com gunicorn app:app faz com que o módulo seja resolvido incorretamente, resultando no erro:

gunicorn.errors.AppImportError:
Failed to find attribute 'app' in 'app'

Executando:

cd app && gunicorn --bind 0.0.0.0:$PORT app:app

o Gunicorn encontra corretamente o arquivo app.py e a variável WSGI:

app = Flask(__name__)

Deploy bem-sucedido

Após aplicar essa configuração, o serviço iniciou normalmente:

* Build: ✅ Sucesso
* Gunicorn: ✅ Inicializado
* Health Check: ✅ HTTP 200
* Deploy: ✅ Concluído

Observações

* Não configure Root Directory como app.
* Utilize app/requirements.txt durante o build.
* O comando de inicialização deve entrar na pasta app antes de iniciar o Gunicorn.
* Caso seja necessário fixar uma versão específica do Python, adicione um arquivo runtime.txt na raiz do projeto.