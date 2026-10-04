# Fundação analítica do dashboard

As fontes são os arquivos oficiais do repositório `StackExchange/Survey` na revisão
`32a114542da67e3759479637343718502742adfd`. O manifesto em `src/data.py` contém URL,
tamanho e SHA-256 de `results.csv` e `schema.csv` para 2023, 2024 e 2025. O carregador
verifica os arquivos antes de usá-los e guarda o cache em `~/.cache/ufrgs-ai-survey/`, fora
deste repositório. A série exclui 2022 e resultados de 2026.

## Schema e cobertura

Uma linha representa uma resposta em um ano. `respondent_id` concatena ano e `ResponseId`;
não é chave longitudinal. Os 20 campos canônicos usam `Int64`, `boolean` e `string` anuláveis.
`role_raw` e `country_raw` preservam as categorias originais; `role_status` separa função
comparável, função conhecida não comparável e resposta ausente.

Na tabela, `A n` significa disponível com *n* valores observados, `NC` significa não coletado
e `IC` significa coletado, mas não comparável ou não harmonizado. As contagens abrangem todos
os respondentes antes dos filtros. O [relatório JSON](foundation-validation.json) detalha
ausências, incompatibilidades e não coleta por campo e ano.

| Campo | Tipo | 2023 (89.184) | 2024 (65.437) | 2025 (49.191) |
|---|---|---:|---:|---:|
| `survey_year` | Int64 | A 89.184 | A 65.437 | A 49.191 |
| `respondent_id` | string | A 89.184 | A 65.437 | A 49.191 |
| `population_group` | string | A 89.184 | A 65.437 | A 49.191 |
| `age_group` | string | A 89.184 | A 65.437 | A 49.191 |
| `role` | string | A 61.387 | A 43.835 | A 30.134 |
| `role_raw` | string | A 76.872 | A 59.445 | A 43.680 |
| `role_status` | string | A 89.184 | A 65.437 | A 49.191 |
| `country` | string | A 87.973 | A 58.930 | A 35.437 |
| `country_raw` | string | A 87.973 | A 58.930 | A 35.437 |
| `ai_current_user` | boolean | A 87.973 | A 60.907 | A 33.720 |
| `ai_daily_user` | boolean | NC | NC | A 33.720 |
| `ai_usage_frequency` | string | NC | NC | A 33.720 |
| `ai_plan_to_use` | boolean | A 87.973 | A 60.907 | A 33.720 |
| `ai_no_plan` | boolean | A 87.973 | A 60.907 | A 33.720 |
| `ai_trust` | string | A 61.396 | A 37.302 | A 33.297 |
| `ai_trust_positive` | boolean | A 61.396 | A 37.302 | A 33.297 |
| `ai_complexity` | string | NC | IC | A 33.283 |
| `work_experience` | Int64 | IC | IC | A 42.893 |
| `ai_agent_usage` | string | NC | NC | A 31.919 |
| `ai_work_change` | string | NC | NC | A 31.678 |

Funções conhecidas sem equivalência entre os instrumentos permanecem nos totais gerais,
mas ficam nulas em `role` e recebem `role_status = not_comparable`. São 15.485 em 2023,
15.610 em 2024 e 13.546 em 2025. Países recebem códigos ISO-3, com aliases explícitos;
`NOMADIC` é uma categoria de residência, não um país, e `XKX` é uma exceção documentada.

## Universos e métricas

O recorte padrão da camada analítica e da interface é população que se declarou profissional,
seis faixas adultas (18+), todas as funções e todos os países. Experiência só é dimensão de
2025. Em 2025, uso diário,
semanal e ocasional compõem `ai_current_user`; intenção de usar permanece separada.

| Indicador | Numerador | Base válida |
|---|---|---|
| Adoção | Usuários atuais | Respostas válidas sobre uso de IA no perfil |
| Uso diário | Usuários diários | Respostas válidas sobre uso de IA no perfil, só 2025 |
| Confiança positiva | `Somewhat trust` ou `Highly trust` | Usuários atuais com resposta válida à pergunta de confiança |
| Uso de agentes | Agentes diários, semanais ou ocasionais | Usuários atuais com resposta válida sobre agentes, só 2025 |
| Capacidade e mudança | Contagem da alternativa | Usuários atuais com resposta válida à pergunta, dentro de cada frequência, só 2025 |

A confiança vem de `AIBen` em 2023 e `AIAcc` em 2024–2025. Respostas neutras entram na base
de confiança como válidas e não positivas. Ausências não viram respostas negativas. Os graus
de mudança por fatores não relacionados à IA são mantidos separados no dataset e agrupados
apenas na visualização. A opção de uso exclusivo em copilot/autocomplete permanece uma
alternativa válida na base de agentes e fica fora de seu numerador.

Toda agregação devolve `metric`, `year`, `numerator`, `valid_denominator`, `percentage`,
`metric_universe`, `filter_state` e `availability_state`. Sem dados, sem respostas válidas,
amostra insuficiente, pergunta não coletada e pergunta incompatível são estados distintos.
Com menos de 50 respostas válidas, as contagens são preservadas e o percentual é nulo.
Esse limite é regra pragmática de apresentação, não garantia estatística.

## Valores reproduzidos no recorte padrão

| Ano | Adoção | Confiança positiva entre usuários atuais |
|---|---:|---:|
| 2023 | 29.381 / 66.684 = 44,1% | 13.533 / 29.283 = 46,2% |
| 2024 | 29.393 / 46.463 = 63,3% | 12.073 / 29.142 = 41,4% |
| 2025 | 20.991 / 25.975 = 80,8% | 7.962 / 20.732 = 38,4% |

Em 2025, as faixas de experiência de 1–5, 6–10, 11–20 e 21+ anos reproduzem, respectivamente,
adoção de 85,2%, 83,2%, 80,2% e 73,7%; uso diário de 55,6%, 52,9%, 50,2% e 43,2%;
confiança de 39,0%, 38,3%, 38,4% e 37,3%. Front-end reproduz 87,2%, 60,0% e 43,3%;
sistemas embarcados, 65,2%, 29,6% e 28,6%.

## Evidências complementares de 2025

`carregar_evidencias_2025()` lê apenas as colunas suplementares do mesmo arquivo oficial
verificado e as une pela chave `2025:ResponseId`. Todas as análises abaixo aplicam os filtros
globais e consideram apenas usuários atuais de IA.

| Evidência | Base válida | Regra |
|---|---|---|
| Frustrações | 19.740 profissionais adultos | Resposta não ausente a `AIFrustration`; múltipla escolha. |
| Workflow | Base específica de cada tarefa (18.660–19.194 no recorte padrão) | Uma das cinco alternativas de `AITool` por tarefa; uso atual parcial/majoritário, intenção parcial/majoritária e ausência de intenção permanecem distintos. |
| Produtividade e precisão dos agentes | 6.739 profissionais adultos usuários atuais de IA e agentes | Resposta válida aos dois itens; numerador requer concordância com produtividade e preocupação com precisão na mesma pessoa. |

No recorte padrão, soluções quase corretas aparecem em 14.967/19.740 (75,8%) e depuração
mais demorada em 9.666/19.740 (49,0%). Buscar respostas tem uso atual de 13.582/19.080
(71,2%); implantação e monitoramento, 2.018/18.660 (10,8%), com 11.241/18.660 (60,2%)
sem intenção de uso. Os planos nessa pergunta referem-se aos próximos **3–5 anos**. Entre
usuários de agentes com ambas as respostas, 4.422/6.739 (65,6%) concordam simultaneamente
que agentes aumentaram sua produtividade e que a precisão os preocupa. São percepções
declaradas; a pergunta de mudança no trabalho não mede produtividade.

## Validação e limites

Execute os testes e a verificação integral no diretório do projeto:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m scripts.validate_foundation --output docs/foundation-validation.json
```

As taxas são descritivas de respondentes auto-selecionados, não estimativas causais.
A redação da pergunta de função em 2025 inclui a função predominante no último ano, criando
comparabilidade parcial em recortes de função. A população de 2025 acrescenta uma categoria
de apoio a desenvolvedores; o filtro “todos os perfis” tem comparabilidade parcial. Menores
de 18 anos não constam nos microdados de 2025, de modo que o recorte de todas as idades não
forma série histórica estritamente comparável. `AIComplex` em 2024 usa alternativas
diferentes das de 2025; experiência de 2023–2024 também tem instrumento incompatível.
