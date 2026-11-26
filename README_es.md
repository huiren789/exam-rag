# ExamRAG

[![tests](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)
[![Live demo](https://img.shields.io/badge/demo-live-green)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R)

<div align="center">

<img src="assets/demo.png" alt="ExamRAG demo: preguntar, recuperar, citar" width="880">

**Repaso de curso con el que puedes verificar cada respuesta**

**Sin dependencias · Trazable · Trae tu propio material** — la búsqueda ocurre localmente, solo se envían al LLM los fragmentos seleccionados y cada respuesta señala la frase exacta de origen.

[Demo en vivo (sin API key)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R) ·
[El problema](#el-problema) ·
[Usa tu curso en 30 segundos](#usa-tu-curso-en-30-segundos)

</div>

**Idioma**：[中文](README.md) · [English](README_en.md) · [日本語](README_ja.md) · [한국어](README_ko.md) · **Español**

> Incluye un curso de *Medición Educativa* de ejemplo, pero **cambia `data/material.txt` y funciona para cualquier asignatura**. El núcleo de búsqueda usa solo la biblioteca estándar de Python. El autor es el primer usuario real, con 4 rondas de iteración sobre un conjunto de evaluación propio.

## El problema

Preguntar directamente a un LLM da respuestas que parecen correctas pero pueden estar inventadas. Leer el libro uno mismo dificulta encontrar el pasaje exacto.

ExamRAG hace localmente el paso de "encontrar el material". La búsqueda es offline, gratuita y visible; solo los fragmentos elegidos se envían al modelo. El prompt exige usar únicamente esos fragmentos, citarlos al final y responder "no mencionado en el material" cuando la respuesta no está en los datos.

## Usa tu curso en 30 segundos

El material incluido es solo un ejemplo. Para usar tus propios apuntes, dales formato de texto plano así:

```text
【Dominado·Nombre del concepto】Texto del concepto, una idea por párrafo.
【Comprendido·Otro concepto】……
【Conocido·Tercer concepto】……
```

Las tres etiquetas (Dominado / Comprendido / Conocido)controlan la ponderación al generar preguntas. Después:

```bash
python -m examrag -q "tu pregunta" --material my.txt
```

O configura `EXAMRAG_MATERIAL=my.txt` una sola vez. La búsqueda, las citas, la generación ponderada de preguntas y la interfaz web funcionan igual — **esta es la diferencia clave frente a una herramienta limitada a un solo curso**.

## Funciones

- Búsqueda léxica local (frecuencia de bigramas, refuerzo de títulos, penalización de índices) — solo biblioteca estándar.
- Búsqueda semántica TF-IDF opcional (`--semantic`) — también offline y sin dependencias.
- Búsqueda vectorial opcional (`--vector`) con caché de embeddings.
- Evidencia a nivel de frase: haz clic en la cita para volver al texto original en la interfaz web.
- Generación ponderada de preguntas (Dominado ×3 / Comprendido ×2 / Conocido ×1).
- Reescritura de consultas, resumen de puntos clave, división de conceptos paralelos.
- Modo `--dry-run` sin conexión: muestra resultados y prompt sin necesidad de API key.
- Interfaz web y FastAPI (5 endpoints con documentación Swagger automática).
- 89 pruebas offline, CI en Python 3.8 / 3.11 / 3.13 + ruff.

## Inicio rápido

```bash
git clone https://github.com/huiren789/exam-rag.git
cd exam-rag
python -m examrag -q "¿Qué es la dificultad?" --dry-run   # offline, sin clave
python -m examrag                                          # modo interactivo
```

Para llamar a un modelo real, copia `.env.example` a `.env` y configura `SILICONFLOW_API_KEY`. La interfaz web usa WorkBuddy Cloud, así que la [demo](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R) no necesita clave.

## Limitaciones

- La búsqueda por defecto es léxica; TF-IDF ayuda con la redacción y los embeddings se necesitan para sinónimos.
- La evidencia usa heurísticas de puntuación china; frases muy largas o que abarcan varias oraciones pueden localizarse con menos precisión.
- El material debe formatearse a mano (sin importación de PDF / Word todavía).
- No hay contexto conversacional; cada pregunta se recupera de forma independiente.

## Documentación

[Documento completo en 中文](README.md) · [English](README_en.md) · [Decisiones de arquitectura](docs/adr) · [Changelog](CHANGELOG.md)

## Licencia

[MIT](LICENSE) © 2026 huiren789
