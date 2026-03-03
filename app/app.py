"""
Reservation Audit Engine — aplicação Flask.
Roda local (localhost:5000) e pronto para deploy no Render (gunicorn).
"""

import os
from flask import Flask, render_template, request, redirect, url_for
from audit_engine import parse_and_audit

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.route("/")
def index():
    return render_template("index.html", error=None)


@app.route("/audit", methods=["POST"])
def audit():
    if "file" not in request.files:
        return render_template("index.html", error="Nenhum arquivo enviado.")

    f = request.files["file"]
    if not f or not f.filename:
        return render_template("index.html", error="Selecione um arquivo XML.")

    if not f.filename.lower().endswith(".xml"):
        return render_template("index.html", error="Apenas arquivos .xml são aceitos.")

    try:
        xml_content = f.read()
        data = parse_and_audit(xml_content)
    except Exception as e:
        return render_template("index.html", error=f"Erro ao processar XML: {e}")

    return render_template("report.html", data=data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
