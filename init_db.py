from pathlib import Path
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import date,timedelta
ROOT=Path(__file__).resolve().parents[1]; DB=ROOT/"database"/"medical_store.db"
schema=(ROOT/"database"/"schema.sql").read_text(encoding="utf-8")
if DB.exists(): DB.unlink()
con=sqlite3.connect(DB); con.executescript(schema)
con.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",("admin",generate_password_hash("admin123"),"System Administrator","ADMIN"))
con.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",("staff",generate_password_hash("staff123"),"Pharmacy Staff","STAFF"))
con.execute("INSERT INTO settings(id,shop_name,address,phone,email,gst_number,invoice_footer) VALUES(1,?,?,?,?,?,?)",
            ("SMART MEDICAL STORE","Main Road, Maharashtra","9999999999","store@example.com","", "Thank you for visiting us."))
suppliers=[("Apollo Distributors","Apollo Healthcare","9876543210","apollo@example.com","Maharashtra","",0),
           ("MediPlus Suppliers","MediPlus","9876501234","mediplus@example.com","Maharashtra","",0)]
for s in suppliers: con.execute("INSERT INTO suppliers(name,company,phone,email,address,gst_number,pending_payment) VALUES(?,?,?,?,?,?,?)",s)
meds=[
("MED001","Paracetamol 500mg","Paracetamol","ABC Pharma","Analgesic","Tablet",20,10,15,5,20,"Room temperature"),
("MED002","Amoxicillin 500mg","Amoxicillin","HealthCare Labs","Antibiotic","Capsule",80,45,65,5,10,"Cool & dry"),
("MED003","Cetirizine 10mg","Cetirizine","Wellness Pharma","Antiallergic","Tablet",35,18,28,5,15,"Room temperature"),
("MED004","ORS Sachet","Oral Rehydration Salts","LifeCare","Hydration","Sachet",25,10,18,5,25,"Dry place"),
("MED005","Pantoprazole 40mg","Pantoprazole","MediCore","Gastro","Tablet",60,30,48,5,15,"Room temperature")]
for m in meds:
    con.execute("""INSERT INTO medicines(code,name,generic_name,manufacturer,category,form,mrp,purchase_price,selling_price,gst,min_stock,storage)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",m)
today=date.today()
batches=[(1,"PCM-A1",today-timedelta(days=120),today+timedelta(days=400),10,20,15,100),
         (2,"AMX-B1",today-timedelta(days=100),today+timedelta(days=250),45,80,65,50),
         (3,"CET-C1",today-timedelta(days=90),today+timedelta(days=45),18,35,28,12),
         (4,"ORS-D1",today-timedelta(days=30),today+timedelta(days=700),10,25,18,80),
         (5,"PAN-E1",today-timedelta(days=80),today-timedelta(days=3),30,60,48,8)]
for b in batches:
    con.execute("""INSERT INTO medicine_batches(medicine_id,batch_no,manufacturing_date,expiry_date,purchase_price,mrp,selling_price,quantity)
                   VALUES(?,?,?,?,?,?,?,?)""",(b[0],b[1],b[2].isoformat(),b[3].isoformat(),b[4],b[5],b[6],b[7]))
con.commit(); con.close(); print("Database initialized:",DB)
