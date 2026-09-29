# Stack Overflow Developer Survey 2025 | AI Analytics Dashboard

An interactive dashboard developed for the **Data Analysis and Visualization** course of the Advanced Artificial Intelligence postgraduate program at UFRGS.

The project explores how developers use AI tools, their perceptions of AI capabilities, and how these technologies influence their professional activities.

## Analyses

Using data from the **Stack Overflow Developer Survey 2025**, the dashboard investigates five questions:

1. Trust in AI accuracy across different usage frequencies.
2. Perceived AI performance on complex tasks.
3. Professional experience and AI adoption.
4. Perceived changes in work practices among AI agent users.
5. Geographic distribution of daily AI usage.

The application features interactive filters, Altair visualizations, and a Folium choropleth map.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/lucao-py/postgrad-ia001-assignment-02.git
cd postgrad-ia001-assignment-02
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the application:

```bash
python -m streamlit run app.py
```

Open the local URL displayed in your terminal, usually `http://localhost:8501`.

## Data Source

[Stack Overflow Developer Survey 2025](https://survey.stackoverflow.co/2025/)

## Academic Context

Developed as Assignment 02 for **IA001 – Data Analysis and Visualization with Python and AI-Assisted Tools**, UFRGS.