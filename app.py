from flask import Flask, request, jsonify, session, send_from_directory, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
from datetime import date, datetime, timedelta
import sqlite3, csv, io, os

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "medical_store.db"
FRONTEND = ROOT / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")
app.secret_key = os.environ.get("MEDICAL_STORE_SECRET", "change-this-secret-in-production")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_if_needed():
    if not DB.exists():
        schema = (ROOT/"database"/"schema.sql").read_text(encoding="utf-8")
        con = db(); con.executescript(schema); con.commit(); con.close()

def current_user():
    return session.get("user")

def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user():
            return jsonify({"error":"Login required"}), 401
        return fn(*a, **kw)
    return wrapper

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u=current_user()
            if not u: return jsonify({"error":"Login required"}), 401
            if u["role"] not in roles: return jsonify({"error":"Permission denied"}), 403
            return fn(*a, **kw)
        return wrapper
    return deco

def iso_today(): return date.today().isoformat()
def expiry_status(exp):
    try:
        d=date.fromisoformat(exp); delta=(d-date.today()).days
        if delta < 0: return "EXPIRED"
        if delta <= 30: return "EXPIRING_30"
        if delta <= 60: return "EXPIRING_60"
        if delta <= 90: return "EXPIRING_90"
        return "VALID"
    except: return "VALID"

@app.get("/")
def index(): return send_from_directory(FRONTEND, "index.html")

@app.post("/api/login")
def login():
    data=request.get_json() or {}
    con=db(); u=con.execute("SELECT * FROM users WHERE username=?", (data.get("username",""),)).fetchone(); con.close()
    if not u or not check_password_hash(u["password_hash"], data.get("password","")):
        return jsonify({"error":"Invalid username or password"}), 401
    session["user"]={"id":u["id"],"username":u["username"],"role":u["role"],"name":u["full_name"]}
    return jsonify({"user":session["user"]})

@app.post("/api/logout")
def logout():
    session.clear(); return jsonify({"ok":True})

@app.get("/api/me")
def me(): return jsonify({"user":current_user()})

@app.get("/api/dashboard")
@login_required
def dashboard():
    con=db()
    med=con.execute("SELECT COUNT(*) c FROM medicines WHERE active=1").fetchone()["c"]
    stock=con.execute("SELECT COALESCE(SUM(quantity),0) q FROM medicine_batches").fetchone()["q"]
    low=con.execute("""SELECT COUNT(*) c FROM medicines m LEFT JOIN medicine_batches b ON b.medicine_id=m.id
                      WHERE m.active=1 GROUP BY m.id HAVING COALESCE(SUM(b.quantity),0)<=m.min_stock""").fetchall()
    out=con.execute("""SELECT COUNT(*) c FROM medicines m LEFT JOIN medicine_batches b ON b.medicine_id=m.id
                      WHERE m.active=1 GROUP BY m.id HAVING COALESCE(SUM(b.quantity),0)=0""").fetchall()
    expired=con.execute("SELECT COUNT(*) c FROM medicine_batches WHERE expiry_date < ?",(iso_today(),)).fetchone()["c"]
    soon=(date.today()+timedelta(days=30)).isoformat()
    expsoon=con.execute("SELECT COUNT(*) c FROM medicine_batches WHERE expiry_date>=? AND expiry_date<=?",(iso_today(),soon)).fetchone()["c"]
    sales=con.execute("SELECT COALESCE(SUM(grand_total),0) x FROM sales WHERE date(sale_date)=date('now','localtime')").fetchone()["x"]
    purchase=con.execute("SELECT COALESCE(SUM(grand_total),0) x FROM purchases WHERE date(purchase_date)=date('now','localtime')").fetchone()["x"]
    profit=con.execute("""SELECT COALESCE(SUM(si.quantity*(si.selling_price-si.purchase_price)-si.discount_amount),0) x
                         FROM sale_items si JOIN sales s ON s.id=si.sale_id
                         WHERE date(s.sale_date)=date('now','localtime')""").fetchone()["x"]
    newstock=con.execute("SELECT COALESCE(SUM(quantity),0) q FROM purchase_items pi JOIN purchases p ON p.id=pi.purchase_id WHERE date(p.purchase_date)=date('now','localtime')").fetchone()["q"]
    con.close()
    return jsonify({"medicines":med,"stock":stock,"low_stock":len(low),"out_of_stock":len(out),
                    "expired":expired,"expiring_soon":expsoon,"today_sales":sales,"today_purchase":purchase,
                    "today_profit":profit,"new_stock":newstock})

@app.get("/api/medicines")
@login_required
def medicines():
    q=request.args.get("q","").strip()
    con=db()
    rows=con.execute("""SELECT m.*, COALESCE(SUM(b.quantity),0) stock,
       MIN(CASE WHEN b.quantity>0 THEN b.expiry_date END) next_expiry
       FROM medicines m LEFT JOIN medicine_batches b ON b.medicine_id=m.id
       WHERE m.active=1 AND (m.name LIKE ? OR m.code LIKE ? OR m.generic_name LIKE ? OR m.manufacturer LIKE ?)
       GROUP BY m.id ORDER BY m.name""", tuple([f"%{q}%"]*4)).fetchall()
    con.close(); return jsonify([dict(r) for r in rows])

@app.post("/api/medicines")
@role_required("ADMIN")
def add_medicine():
    d=request.get_json() or {}
    required=["code","name","generic_name","manufacturer","category","form","mrp","selling_price","gst","min_stock"]
    if any(d.get(k) in (None,"") for k in required): return jsonify({"error":"Fill all required medicine fields"}),400
    con=db()
    try:
        cur=con.execute("""INSERT INTO medicines(code,name,generic_name,manufacturer,category,form,mrp,purchase_price,
                           selling_price,gst,min_stock,storage,active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (d["code"],d["name"],d["generic_name"],d["manufacturer"],d["category"],d["form"],float(d["mrp"]),
             float(d.get("purchase_price",0)),float(d["selling_price"]),float(d["gst"]),int(d["min_stock"]),d.get("storage","")))
        con.commit(); return jsonify({"id":cur.lastrowid})
    except sqlite3.IntegrityError: return jsonify({"error":"Medicine code already exists"}),400
    finally: con.close()

@app.put("/api/medicines/<int:mid>")
@role_required("ADMIN")
def edit_medicine(mid):
    d=request.get_json() or {}; con=db()
    con.execute("""UPDATE medicines SET code=?,name=?,generic_name=?,manufacturer=?,category=?,form=?,mrp=?,
       purchase_price=?,selling_price=?,gst=?,min_stock=?,storage=? WHERE id=?""",
       (d["code"],d["name"],d["generic_name"],d["manufacturer"],d["category"],d["form"],float(d["mrp"]),
        float(d.get("purchase_price",0)),float(d["selling_price"]),float(d["gst"]),int(d["min_stock"]),d.get("storage",""),mid))
    con.commit(); con.close(); return jsonify({"ok":True})

@app.delete("/api/medicines/<int:mid>")
@role_required("ADMIN")
def delete_medicine(mid):
    con=db(); con.execute("UPDATE medicines SET active=0 WHERE id=?",(mid,)); con.commit(); con.close()
    return jsonify({"ok":True})

@app.get("/api/batches/<int:mid>")
@login_required
def batches(mid):
    con=db(); rows=con.execute("""SELECT b.*,m.name,m.code FROM medicine_batches b JOIN medicines m ON m.id=b.medicine_id
                                  WHERE b.medicine_id=? ORDER BY date(b.expiry_date) ASC""",(mid,)).fetchall(); con.close()
    out=[dict(r) for r in rows]
    for r in out: r["status"]=expiry_status(r["expiry_date"])
    return jsonify(out)

@app.get("/api/stock")
@login_required
def stock():
    con=db(); rows=con.execute("""SELECT b.id,b.batch_no,b.expiry_date,b.quantity,b.purchase_price,b.mrp,
       m.id medicine_id,m.code,m.name,m.min_stock FROM medicine_batches b JOIN medicines m ON m.id=b.medicine_id
       ORDER BY date(b.expiry_date),m.name""").fetchall(); con.close()
    return jsonify([dict(r, status=expiry_status(r["expiry_date"])) for r in rows])

@app.get("/api/expiry")
@login_required
def expiry():
    window=int(request.args.get("days","90")); con=db()
    rows=con.execute("""SELECT b.*,m.code,m.name FROM medicine_batches b JOIN medicines m ON m.id=b.medicine_id
                        WHERE b.expiry_date<=date('now', ?) ORDER BY date(b.expiry_date)""",(f"+{window} day",)).fetchall()
    con.close(); return jsonify([dict(r,status=expiry_status(r["expiry_date"])) for r in rows])

@app.post("/api/purchases")
@role_required("ADMIN","STAFF")
def purchase():
    d=request.get_json() or {}; items=d.get("items",[])
    if not items: return jsonify({"error":"Add at least one item"}),400
    con=db()
    try:
        total=sum(float(x["quantity"])*float(x["purchase_price"]) for x in items)
        cur=con.execute("""INSERT INTO purchases(invoice_no,supplier_id,purchase_date,subtotal,gst_amount,discount_amount,grand_total,payment_status)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (d.get("invoice_no","AUTO-"+datetime.now().strftime("%Y%m%d%H%M%S")),d.get("supplier_id"),
                         datetime.now().isoformat(timespec="seconds"),total,0,0,total,d.get("payment_status","PAID")))
        pid=cur.lastrowid
        for x in items:
            mid=int(x["medicine_id"]); qty=int(x["quantity"]); batch=x["batch_no"].strip()
            con.execute("""INSERT INTO purchase_items(purchase_id,medicine_id,batch_no,quantity,purchase_price,mrp,gst,expiry_date)
                           VALUES(?,?,?,?,?,?,?,?)""",(pid,mid,batch,qty,float(x["purchase_price"]),float(x["mrp"]),float(x.get("gst",0)),x["expiry_date"]))
            b=con.execute("SELECT id FROM medicine_batches WHERE medicine_id=? AND batch_no=?",(mid,batch)).fetchone()
            if b:
                con.execute("UPDATE medicine_batches SET quantity=quantity+?,purchase_price=?,mrp=?,expiry_date=? WHERE id=?",
                            (qty,float(x["purchase_price"]),float(x["mrp"]),x["expiry_date"],b["id"]))
                bid=b["id"]
            else:
                bid=con.execute("""INSERT INTO medicine_batches(medicine_id,batch_no,manufacturing_date,expiry_date,
                                  purchase_price,mrp,selling_price,quantity) VALUES(?,?,?,?,?,?,?,?)""",
                                (mid,batch,x.get("manufacturing_date"),x["expiry_date"],float(x["purchase_price"]),
                                 float(x["mrp"]),float(x.get("selling_price",x["mrp"])),qty)).lastrowid
            con.execute("""INSERT INTO stock_transactions(batch_id,type,quantity,reference_type,reference_id,notes)
                           VALUES(?,?,?,?,?,?)""",(bid,"PURCHASE",qty,"PURCHASE",pid,"New stock"))
        con.commit(); return jsonify({"purchase_id":pid,"grand_total":total})
    except Exception as e:
        con.rollback(); return jsonify({"error":str(e)}),400
    finally: con.close()

@app.post("/api/sales")
@role_required("ADMIN","STAFF")
def sale():
    d=request.get_json() or {}; items=d.get("items",[])
    if not items: return jsonify({"error":"Cart is empty"}),400
    con=db()
    try:
        subtotal=sum(float(x["quantity"])*float(x["selling_price"]) for x in items)
        discount=sum(float(x.get("discount",0)) for x in items)
        gst=sum(float(x.get("gst_amount",0)) for x in items)
        grand=subtotal-discount+gst
        bill=d.get("bill_no") or "INV-"+datetime.now().strftime("%Y%m%d%H%M%S")
        cur=con.execute("""INSERT INTO sales(bill_no,customer_id,sale_date,subtotal,discount_amount,gst_amount,grand_total,payment_method,user_id)
                           VALUES(?,?,?,?,?,?,?,?,?)""",(bill,d.get("customer_id"),datetime.now().isoformat(timespec="seconds"),
                           subtotal,discount,gst,grand,d.get("payment_method","CASH"),current_user()["id"]))
        sid=cur.lastrowid
        for x in items:
            qty=int(x["quantity"]); bid=int(x["batch_id"])
            b=con.execute("""SELECT b.*,m.name,m.code,m.gst FROM medicine_batches b JOIN medicines m ON m.id=b.medicine_id WHERE b.id=?""",(bid,)).fetchone()
            if not b: raise ValueError("Batch not found")
            if expiry_status(b["expiry_date"])=="EXPIRED": raise ValueError(f'{b["name"]} batch is expired')
            if b["quantity"]<qty: raise ValueError(f'Insufficient stock for {b["name"]}')
            sp=float(x["selling_price"]); disc=float(x.get("discount",0)); ga=float(x.get("gst_amount",0))
            con.execute("""INSERT INTO sale_items(sale_id,batch_id,medicine_id,quantity,selling_price,purchase_price,discount_amount,gst_amount,total)
                           VALUES(?,?,?,?,?,?,?,?,?)""",(sid,bid,b["medicine_id"],qty,sp,b["purchase_price"],disc,ga,qty*sp-disc+ga))
            con.execute("UPDATE medicine_batches SET quantity=quantity-? WHERE id=?",(qty,bid))
            con.execute("""INSERT INTO stock_transactions(batch_id,type,quantity,reference_type,reference_id,notes)
                           VALUES(?,?,?,?,?,?)""",(bid,"SALE",-qty,"SALE",sid,"POS sale"))
        con.execute("INSERT INTO payments(sale_id,amount,method,paid_at) VALUES(?,?,?,?)",(sid,grand,d.get("payment_method","CASH"),datetime.now().isoformat(timespec="seconds")))
        con.commit(); return jsonify({"sale_id":sid,"bill_no":bill,"grand_total":grand})
    except Exception as e:
        con.rollback(); return jsonify({"error":str(e)}),400
    finally: con.close()

@app.get("/api/sales")
@login_required
def sales():
    con=db(); rows=con.execute("""SELECT s.*,COALESCE(c.name,'Walk-in Customer') customer
                                  FROM sales s LEFT JOIN customers c ON c.id=s.customer_id ORDER BY s.id DESC LIMIT 500""").fetchall(); con.close()
    return jsonify([dict(r) for r in rows])

@app.get("/api/purchases")
@login_required
def purchases():
    con=db(); rows=con.execute("""SELECT p.*,COALESCE(s.name,'-') supplier FROM purchases p
                                  LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.id DESC LIMIT 500""").fetchall(); con.close()
    return jsonify([dict(r) for r in rows])

@app.get("/api/bills/<int:sid>")
@login_required
def bill(sid):
    con=db()
    s=con.execute("""SELECT s.*,COALESCE(c.name,'Walk-in Customer') customer,COALESCE(c.mobile,'') mobile
                     FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE s.id=?""",(sid,)).fetchone()
    items=con.execute("""SELECT si.*,m.name,m.code,b.batch_no,b.expiry_date FROM sale_items si
                         JOIN medicines m ON m.id=si.medicine_id JOIN medicine_batches b ON b.id=si.batch_id WHERE si.sale_id=?""",(sid,)).fetchall()
    settings=con.execute("SELECT * FROM settings LIMIT 1").fetchone(); con.close()
    if not s: return jsonify({"error":"Bill not found"}),404
    return jsonify({"sale":dict(s),"items":[dict(x) for x in items],"shop":dict(settings) if settings else {}})

@app.get("/api/customers")
@login_required
def customers():
    con=db(); rows=con.execute("""SELECT c.*,COUNT(s.id) visits,COALESCE(SUM(s.grand_total),0) total_purchases
                                  FROM customers c LEFT JOIN sales s ON s.customer_id=c.id GROUP BY c.id ORDER BY c.name""").fetchall(); con.close()
    return jsonify([dict(r) for r in rows])

@app.post("/api/customers")
@role_required("ADMIN","STAFF")
def add_customer():
    d=request.get_json() or {}; con=db()
    cur=con.execute("INSERT INTO customers(name,mobile,address) VALUES(?,?,?)",(d.get("name",""),d.get("mobile",""),d.get("address","")))
    con.commit(); con.close(); return jsonify({"id":cur.lastrowid})

@app.get("/api/suppliers")
@login_required
def suppliers():
    con=db(); rows=con.execute("""SELECT s.*,COUNT(p.id) purchases,COALESCE(SUM(p.grand_total),0) total_purchases
                                  FROM suppliers s LEFT JOIN purchases p ON p.supplier_id=s.id GROUP BY s.id ORDER BY s.name""").fetchall(); con.close()
    return jsonify([dict(r) for r in rows])

@app.post("/api/suppliers")
@role_required("ADMIN")
def add_supplier():
    d=request.get_json() or {}; con=db()
    cur=con.execute("""INSERT INTO suppliers(name,company,phone,email,address,gst_number,pending_payment)
                       VALUES(?,?,?,?,?,?,?)""",(d.get("name",""),d.get("company",""),d.get("phone",""),d.get("email",""),
                       d.get("address",""),d.get("gst_number",""),float(d.get("pending_payment",0))))
    con.commit(); con.close(); return jsonify({"id":cur.lastrowid})

@app.post("/api/stock/adjust")
@role_required("ADMIN")
def adjust_stock():
    d=request.get_json() or {}; qty=int(d["quantity"]); typ=d["type"].upper()
    if typ not in ("DAMAGE","RETURN_IN","RETURN_OUT","EXPIRED"): return jsonify({"error":"Invalid adjustment"}),400
    con=db()
    b=con.execute("SELECT quantity FROM medicine_batches WHERE id=?",(int(d["batch_id"]),)).fetchone()
    if not b: con.close(); return jsonify({"error":"Batch not found"}),404
    delta = qty if typ=="RETURN_IN" else -qty
    if b["quantity"]+delta < 0: con.close(); return jsonify({"error":"Not enough stock"}),400
    con.execute("UPDATE medicine_batches SET quantity=quantity+? WHERE id=?",(delta,int(d["batch_id"])))
    con.execute("""INSERT INTO stock_transactions(batch_id,type,quantity,reference_type,reference_id,notes)
                   VALUES(?,?,?,?,?,?)""",(int(d["batch_id"]),typ,delta,"ADJUSTMENT",None,d.get("notes","")))
    con.commit(); con.close(); return jsonify({"ok":True})

@app.get("/api/reports")
@login_required
def reports():
    con=db()
    sales=con.execute("""SELECT date(sale_date) day,ROUND(SUM(grand_total),2) total,COUNT(*) bills
                         FROM sales GROUP BY date(sale_date) ORDER BY day DESC LIMIT 31""").fetchall()
    profit=con.execute("""SELECT ROUND(COALESCE(SUM(si.quantity*(si.selling_price-si.purchase_price)-si.discount_amount),0),2) profit
                          FROM sale_items si""").fetchone()["profit"]
    valuation=con.execute("""SELECT ROUND(COALESCE(SUM(quantity*purchase_price),0),2) value FROM medicine_batches""").fetchone()["value"]
    con.close(); return jsonify({"daily_sales":[dict(x) for x in sales],"total_profit":profit,"stock_valuation":valuation})

@app.get("/api/search")
@login_required
def search():
    q=request.args.get("q","").strip()
    con=db(); rows=con.execute("""SELECT m.id,m.code,m.name,m.generic_name,m.manufacturer,COALESCE(SUM(b.quantity),0) stock
                                  FROM medicines m LEFT JOIN medicine_batches b ON b.medicine_id=m.id
                                  WHERE m.active=1 AND (m.name LIKE ? OR m.code LIKE ? OR m.generic_name LIKE ? OR m.manufacturer LIKE ?)
                                  GROUP BY m.id ORDER BY m.name LIMIT 50""",tuple([f"%{q}%"]*4)).fetchall(); con.close()
    return jsonify([dict(r) for r in rows])

@app.get("/api/settings")
@login_required
def get_settings():
    con=db(); r=con.execute("SELECT * FROM settings LIMIT 1").fetchone(); con.close(); return jsonify(dict(r) if r else {})

@app.put("/api/settings")
@role_required("ADMIN")
def update_settings():
    d=request.get_json() or {}; con=db()
    con.execute("""UPDATE settings SET shop_name=?,address=?,phone=?,email=?,gst_number=?,invoice_footer=? WHERE id=1""",
                (d.get("shop_name",""),d.get("address",""),d.get("phone",""),d.get("email",""),d.get("gst_number",""),d.get("invoice_footer","")))
    con.commit(); con.close(); return jsonify({"ok":True})

@app.get("/api/reports/export.csv")
@login_required
def export_sales():
    con=db(); rows=con.execute("SELECT bill_no,sale_date,grand_total,payment_method FROM sales ORDER BY id DESC").fetchall(); con.close()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Bill No","Date","Grand Total","Payment Method"])
    for r in rows: w.writerow([r["bill_no"],r["sale_date"],r["grand_total"],r["payment_method"]])
    resp=make_response(out.getvalue()); resp.headers["Content-Disposition"]="attachment; filename=sales_report.csv"; resp.headers["Content-Type"]="text/csv"
    return resp

init_if_needed()
if __name__=="__main__": app.run(host="127.0.0.1",port=5000,debug=False)
