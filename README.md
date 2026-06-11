# Lembretes Hermes Web App

Aplicação simples para cadastrar lembretes com texto e horários.

Arquivos:
- app.py: tela web local em http://127.0.0.1:8080
- runner.py: verifica os lembretes e envia para Telegram
- data/lembretes.json: arquivo com lembretes
- logs/runner.log: log de envio

Cron do runner:
* * * * * /usr/bin/python3 /home/ubuntu/automacoes/lembretes_app/runner.py >> /home/ubuntu/automacoes/lembretes_app/logs/runner_cron.log 2>&1
