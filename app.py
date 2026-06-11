#!/usr/bin/env python3
import json
import html
import uuid
from pathlib import Path
from urllib.parse import parse_qs, quote
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

BASE_DIR = Path("/home/ubuntu/automacoes/lembretes_app")
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
REMINDERS_FILE = DATA_DIR / "lembretes.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

if not REMINDERS_FILE.exists():
    REMINDERS_FILE.write_text("[]", encoding="utf-8")


def load_reminders():
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_reminders(reminders):
    REMINDERS_FILE.write_text(json.dumps(reminders, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_times(raw):
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    times = []
    for p in parts:
        if not p:
            continue
        if len(p) == 4 and p[1] == ":":
            p = "0" + p
        try:
            datetime.strptime(p, "%H:%M")
        except ValueError:
            raise ValueError(f"Horario invalido: {p}. Use formato HH:MM, exemplo 11:30")
        times.append(p)
    if not times:
        raise ValueError("Informe pelo menos um horario.")
    return sorted(set(times))


def render_page(message=""):
    reminders = load_reminders()
    rows = ""

    for r in reminders:
        rid = html.escape(r.get("id", ""))
        text = html.escape(r.get("text", ""))
        times = html.escape(", ".join(r.get("times", [])))
        days = html.escape(r.get("days", "daily"))
        active = r.get("active", True)
        status = "Ativo" if active else "Pausado"
        toggle_label = "Pausar" if active else "Ativar"

        rows += f"""
        <tr>
          <td>{text}</td>
          <td>{times}</td>
          <td>{days}</td>
          <td>{status}</td>
          <td class="actions">
            <form method="post" action="/toggle">
              <input type="hidden" name="id" value="{rid}">
              <button type="submit">{toggle_label}</button>
            </form>
            <form method="post" action="/delete" onsubmit="return confirm('Apagar este lembrete?')">
              <input type="hidden" name="id" value="{rid}">
              <button class="danger" type="submit">Apagar</button>
            </form>
          </td>
        </tr>
        """

    if not rows:
        rows = '<tr><td colspan="5" class="empty">Nenhum lembrete cadastrado.</td></tr>'

    escaped_message = html.escape(message)
    notice = f'<div class="notice">{escaped_message}</div>' if escaped_message else ""

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Lembretes Hermes</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f3f4f6; color: #111827; }}
    header {{ background: #111827; color: white; padding: 18px 24px; }}
    main {{ max-width: 980px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }}
    label {{ display: block; font-weight: bold; margin: 12px 0 6px; }}
    input, textarea, select {{ width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; box-sizing: border-box; font-size: 15px; }}
    textarea {{ min-height: 80px; }}
    button {{ background: #2563eb; color: white; border: none; border-radius: 8px; padding: 10px 14px; cursor: pointer; font-weight: bold; margin-top: 12px; }}
    button:hover {{ opacity: .9; }}
    button.danger {{ background: #dc2626; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; border-bottom: 1px solid #e5e7eb; padding: 10px; vertical-align: top; }}
    th {{ background: #f9fafb; }}
    .actions form {{ display: inline-block; margin-right: 6px; }}
    .notice {{ background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 10px; border-radius: 8px; margin-bottom: 16px; }}
    .hint {{ color: #4b5563; font-size: 14px; }}
    .empty {{ color: #6b7280; text-align: center; }}
  </style>
</head>
<body>
  <header>
    <h1>Lembretes Hermes</h1>
    <div>Cadastre texto e horario. O envio vai para seu Telegram.</div>
  </header>
  <main>
    {notice}
    <section class="card">
      <h2>Novo lembrete</h2>
      <form method="post" action="/add">
        <label>Texto do lembrete</label>
        <textarea name="text" required placeholder="Exemplo: Está na hora do curso"></textarea>
        <label>Horarios</label>
        <input name="times" required placeholder="Exemplo: 11:30 ou 08:00, 14:00, 20:00">
        <div class="hint">Use formato 24h. Para mais de um horario, separe por virgula.</div>
        <label>Dias</label>
        <select name="days">
          <option value="daily">Todos os dias</option>
          <option value="weekdays">Segunda a sexta</option>
          <option value="weekends">Sabado e domingo</option>
        </select>
        <button type="submit">Salvar lembrete</button>
      </form>
    </section>
    <section class="card">
      <h2>Lembretes cadastrados</h2>
      <table>
        <thead>
          <tr><th>Texto</th><th>Horarios</th><th>Dias</th><th>Status</th><th>Acoes</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
  </main>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def redirect(self, message=""):
        location = "/"
        if message:
            location = "/?msg=" + quote(message)
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return {k: v[0] for k, v in parse_qs(body).items()}

    def do_GET(self):
        msg = ""
        if self.path.startswith("/?"):
            query = self.path.split("?", 1)[1]
            msg = parse_qs(query).get("msg", [""])[0]

        content = render_page(msg).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        try:
            form = self.read_form()
            reminders = load_reminders()

            if self.path == "/add":
                text = form.get("text", "").strip()
                times = normalize_times(form.get("times", ""))
                days = form.get("days", "daily").strip()

                if not text:
                    raise ValueError("Informe o texto do lembrete.")

                reminders.append({
                    "id": str(uuid.uuid4())[:8],
                    "text": text,
                    "times": times,
                    "days": days,
                    "active": True,
                    "last_sent": {}
                })
                save_reminders(reminders)
                self.redirect("Lembrete salvo com sucesso.")
                return

            if self.path == "/toggle":
                rid = form.get("id", "")
                for r in reminders:
                    if r.get("id") == rid:
                        r["active"] = not r.get("active", True)
                save_reminders(reminders)
                self.redirect("Status atualizado.")
                return

            if self.path == "/delete":
                rid = form.get("id", "")
                reminders = [r for r in reminders if r.get("id") != rid]
                save_reminders(reminders)
                self.redirect("Lembrete apagado.")
                return

            self.send_error(404)
        except Exception as e:
            self.redirect(f"Erro: {e}")


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8080
    print(f"Lembretes Hermes rodando em http://{host}:{port}")
    HTTPServer((host, port), Handler).serve_forever()
