Railway WhatsApp Confirmed Alerts v1
Start: python whatsapp_confirmed_alerts.py

Required:
NEON_DATABASE_URL
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_TO_NUMBER

Optional:
POLL_SECONDS=180
DRY_RUN=false
WHATSAPP_GRAPH_VERSION=v23.0
WHATSAPP_TEMPLATE_NAME=
WHATSAPP_TEMPLATE_LANG=en_US

Sends ONLY new CONFIRMED LONG / CONFIRMED SHORT transitions.
Stock source: public.early_detector_snapshots.
Index: supplied dashboard currently computes states in memory and does not persist them, so v1 deliberately does not approximate index signals.

ONE-TIME RAILWAY TEST:
1. Add SEND_TEST_MESSAGE=true in Railway Variables.
2. Redeploy.
3. You should receive: WHATSAPP INTEGRATION TEST.
4. After success, change SEND_TEST_MESSAGE=false and redeploy.
The test run exits after sending one message, so it cannot repeatedly spam the phone.
