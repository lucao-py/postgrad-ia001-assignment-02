# IA no Desenvolvimento de Software

Dashboard da disciplina IA001 (UFRGS) com as pesquisas oficiais do Stack Overflow Developer Survey de 2023, 2024 e 2025. A análise acompanha a expansão do uso atual de IA e da confiança entre usuários atuais, compara perfis profissionais de 2025 e examina capacidade percebida, frustrações, adoção por tarefa e mudanças no trabalho.

A visualização histórica usa a mesma escala de 0–100% para duas taxas com **bases distintas**. O uso atual considera respostas válidas sobre uso de IA; a confiança considera somente usuários atuais com resposta válida de confiança. O recorte padrão inclui profissionais de 18 anos ou mais. As abas apresentam perfis e, em sequência, capacidade, frustrações, uso por tarefa e mudança percebida. O fechamento sobre agentes usa respostas válidas de produtividade percebida e preocupação com precisão dos mesmos usuários.

## Executar

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Na primeira execução, os arquivos anuais são baixados para `~/.cache/ufrgs-ai-survey/` e verificados por tamanho e SHA-256 antes da análise. As versões, o schema, a cobertura, as bases dos indicadores, os resultados de referência e os limites estão em [Fundação analítica](docs/analytical-foundation.md).

## Verificar

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -m scripts.validate_foundation --output docs/foundation-validation.json
```

Os testes usam a biblioteca padrão `unittest` e o teste de interface do Streamlit. A validação integral lê novamente as fontes oficiais verificadas e confere contagens, denominadores, percentuais, perfis e cobertura. Ela falha diante de qualquer divergência.
