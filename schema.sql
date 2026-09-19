CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 full_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('ADMIN','STAFF')), active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS medicines(
 id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, generic_name TEXT,
 manufacturer TEXT, category TEXT, form TEXT, mrp REAL DEFAULT 0, purchase_price REAL DEFAULT 0,
 selling_price REAL DEFAULT 0, gst REAL DEFAULT 0, min_stock INTEGER DEFAULT 0, storage TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS suppliers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,company TEXT,phone TEXT,email TEXT,address TEXT,
 gst_number TEXT,pending_payment REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS customers(
 id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,mobile TEXT,address TEXT);
CREATE TABLE IF NOT EXISTS medicine_batches(
 id INTEGER PRIMARY KEY AUTOINCREMENT,medicine_id INTEGER NOT NULL,batch_no TEXT NOT NULL,
 manufacturing_date TEXT,expiry_date TEXT NOT NULL,purchase_price REAL DEFAULT 0,mrp REAL DEFAULT 0,
 selling_price REAL DEFAULT 0,quantity INTEGER DEFAULT 0,
 UNIQUE(medicine_id,batch_no),FOREIGN KEY(medicine_id) REFERENCES medicines(id));
CREATE TABLE IF NOT EXISTS purchases(
 id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_no TEXT UNIQUE,supplier_id INTEGER,purchase_date TEXT,
 subtotal REAL DEFAULT 0,gst_amount REAL DEFAULT 0,discount_amount REAL DEFAULT 0,grand_total REAL DEFAULT 0,
 payment_status TEXT DEFAULT 'PAID',FOREIGN KEY(supplier_id) REFERENCES suppliers(id));
CREATE TABLE IF NOT EXISTS purchase_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,purchase_id INTEGER NOT NULL,medicine_id INTEGER NOT NULL,batch_no TEXT,
 quantity INTEGER,purchase_price REAL,mrp REAL,gst REAL,expiry_date TEXT,
 FOREIGN KEY(purchase_id) REFERENCES purchases(id),FOREIGN KEY(medicine_id) REFERENCES medicines(id));
CREATE TABLE IF NOT EXISTS sales(
 id INTEGER PRIMARY KEY AUTOINCREMENT,bill_no TEXT UNIQUE,customer_id INTEGER,sale_date TEXT,subtotal REAL,
 discount_amount REAL,gst_amount REAL,grand_total REAL,payment_method TEXT,user_id INTEGER,
 FOREIGN KEY(customer_id) REFERENCES customers(id),FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS sale_items(
 id INTEGER PRIMARY KEY AUTOINCREMENT,sale_id INTEGER NOT NULL,batch_id INTEGER NOT NULL,medicine_id INTEGER NOT NULL,
 quantity INTEGER,selling_price REAL,purchase_price REAL,discount_amount REAL,gst_amount REAL,total REAL,
 FOREIGN KEY(sale_id) REFERENCES sales(id),FOREIGN KEY(batch_id) REFERENCES medicine_batches(id),
 FOREIGN KEY(medicine_id) REFERENCES medicines(id));
CREATE TABLE IF NOT EXISTS payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,sale_id INTEGER,amount REAL,method TEXT,paid_at TEXT,
 FOREIGN KEY(sale_id) REFERENCES sales(id));
CREATE TABLE IF NOT EXISTS stock_transactions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,batch_id INTEGER,type TEXT,quantity INTEGER,reference_type TEXT,reference_id INTEGER,
 notes TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(batch_id) REFERENCES medicine_batches(id));
CREATE TABLE IF NOT EXISTS settings(
 id INTEGER PRIMARY KEY CHECK(id=1),shop_name TEXT,address TEXT,phone TEXT,email TEXT,gst_number TEXT,invoice_footer TEXT);
CREATE INDEX IF NOT EXISTS idx_medicine_name ON medicines(name);
CREATE INDEX IF NOT EXISTS idx_batch_expiry ON medicine_batches(expiry_date);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
