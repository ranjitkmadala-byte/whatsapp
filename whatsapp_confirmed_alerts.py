import os,time,logging
from datetime import datetime,time as dt
from zoneinfo import ZoneInfo
import psycopg,requests
from psycopg.rows import dict_row

IST=ZoneInfo("Asia/Kolkata")
DB=os.environ["NEON_DATABASE_URL"]
TOKEN=os.environ["WHATSAPP_ACCESS_TOKEN"]
PHONE_ID=os.environ["WHATSAPP_PHONE_NUMBER_ID"]
TO=os.environ["WHATSAPP_TO_NUMBER"].replace("+","").replace(" ","")
POLL=int(os.getenv("POLL_SECONDS","180"))
GRAPH=os.getenv("WHATSAPP_GRAPH_VERSION","v23.0")
TEMPLATE=os.getenv("WHATSAPP_TEMPLATE_NAME","").strip()
LANG=os.getenv("WHATSAPP_TEMPLATE_LANG","en_US")
DRY=os.getenv("DRY_RUN","false").lower()=="true"
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s")
log=logging.getLogger("wa-alert")

def db():
    return psycopg.connect(DB,row_factory=dict_row,connect_timeout=10)

def setup():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS public.whatsapp_detector_alerts(
          id BIGSERIAL PRIMARY KEY,trading_date DATE NOT NULL,source TEXT NOT NULL,
          symbol TEXT NOT NULL,signal_ts TIMESTAMPTZ NOT NULL,state TEXT NOT NULL,
          score NUMERIC,sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          provider_message_id TEXT,UNIQUE(source,symbol,signal_ts,state));""")
        c.commit()

def stock_events():
    sql="""WITH d AS(SELECT MAX(trading_date)d FROM public.early_detector_snapshots),
    x AS(SELECT e.*,LAG(state)OVER(PARTITION BY symbol ORDER BY ts)prev_state
    FROM public.early_detector_snapshots e WHERE trading_date=(SELECT d FROM d))
    SELECT trading_date,'STOCK'::text source,symbol,ts signal_ts,state,score,prev_state
    FROM x WHERE state IN('CONFIRMED LONG','CONFIRMED SHORT')
    AND COALESCE(prev_state,'')<>state ORDER BY ts"""
    with db() as c:return c.execute(sql).fetchall()

def sent(r):
    with db() as c:
        return c.execute("""SELECT 1 FROM public.whatsapp_detector_alerts
        WHERE source=%s AND symbol=%s AND signal_ts=%s AND state=%s""",
        (r["source"],r["symbol"],r["signal_ts"],r["state"])).fetchone() is not None

def mark(r,mid):
    with db() as c:
        c.execute("""INSERT INTO public.whatsapp_detector_alerts
        (trading_date,source,symbol,signal_ts,state,score,provider_message_id)
        VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (r["trading_date"],r["source"],r["symbol"],r["signal_ts"],r["state"],r["score"],mid))
        c.commit()

def send(r):
    ts=r["signal_ts"]
    if ts.tzinfo is None:ts=ts.replace(tzinfo=ZoneInfo("UTC"))
    t=ts.astimezone(IST).strftime("%H:%M")
    score="-" if r["score"] is None else f'{float(r["score"]):.1f}/10'
    text=f'{r["state"]} — {r["symbol"]}\nTime: {t} IST | Score: {score}'
    if DRY:
        log.info("DRY | "+text.replace("\n"," | "));return "dry"
    url=f"https://graph.facebook.com/{GRAPH}/{PHONE_ID}/messages"
    h={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"}
    if TEMPLATE:
        payload={"messaging_product":"whatsapp","to":TO,"type":"template",
          "template":{"name":TEMPLATE,"language":{"code":LANG},"components":[{
          "type":"body","parameters":[{"type":"text","text":r["state"]},
          {"type":"text","text":r["symbol"]},{"type":"text","text":t},{"type":"text","text":score}]}]}}
    else:
        payload={"messaging_product":"whatsapp","to":TO,"type":"text","text":{"body":text}}
    x=requests.post(url,headers=h,json=payload,timeout=20);x.raise_for_status()
    return (x.json().get("messages")or[{}])[0].get("id")

def open_market():
    n=datetime.now(IST)
    return n.weekday()<5 and dt(9,15)<=n.time()<=dt(15,35)

def main():
    setup();log.info("Confirmed-only monitor started")
    while True:
        try:
            if open_market():
                for r in stock_events():
                    if not sent(r):
                        mid=send(r);mark(r,mid);log.info("SENT %s %s",r["symbol"],r["state"])
        except Exception:log.exception("cycle failed")
        time.sleep(POLL)

if __name__=="__main__":main()
