const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);
let user=null, page="dashboard", medicines=[], cart=[];
const money=n=>"₹"+Number(n||0).toFixed(2);
async function api(url,opt={}){let r=await fetch(url,{headers:{"Content-Type":"application/json"},...opt});let d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||"Request failed");return d}
function toast(t){let x=$("#toast");x.textContent=t;x.style.cssText="position:fixed;right:20px;top:20px;background:#172033;color:#fff;padding:12px 16px;border-radius:10px;z-index:99";setTimeout(()=>x.style.cssText="",2600)}
$("#loginForm").onsubmit=async e=>{e.preventDefault();try{let d=await api("/api/login",{method:"POST",body:JSON.stringify({username:$("#username").value,password:$("#password").value})});user=d.user;boot()}catch(e){toast(e.message)}};
async function boot(){ $("#loginView").classList.add("hidden");$("#appView").classList.remove("hidden");$("#userName").textContent=user.name;$("#userRole").textContent=user.role; if(user.role!=="ADMIN")$$(".admin-only").forEach(x=>x.style.display="none"); await show("dashboard")}
$("#logout").onclick=async()=>{await api("/api/logout",{method:"POST"});location.reload()};
$("#nav").onclick=e=>{let b=e.target.closest("button[data-page]");if(b)show(b.dataset.page)};
$("#globalSearch").oninput=async e=>{if(e.target.value.length<2)return;let d=await api("/api/search?q="+encodeURIComponent(e.target.value));$("#content").innerHTML=`<div class="panel"><h3>Search Results</h3>${table(d,[["code","Code"],["name","Medicine"],["generic_name","Generic"],["manufacturer","Manufacturer"],["stock","Stock"]])}</div>`};
setInterval(()=>$("#clock").textContent=new Date().toLocaleString(),1000);
async function show(p){page=p;$$("nav button").forEach(x=>x.classList.toggle("active",x.dataset.page===p));$("#pageTitle").textContent=p.replaceAll("_"," ").replace(/\b\w/g,x=>x.toUpperCase());let fn={dashboard:dashboard,medicines:medicinePage,stock:stockPage,expiry:expiryPage,purchase:purchasePage,pos:posPage,sales:salesPage,purchases:purchasesPage,customers:customerPage,suppliers:supplierPage,reports:reportsPage,settings:settingsPage}[p];await fn()}
function table(rows,cols){return `<div style="overflow:auto"><table class="table"><thead><tr>${cols.map(c=>`<th>${c[1]}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${r[c[0]]??"-"}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`}
async function dashboard(){
 let d=await api("/api/dashboard"),r=await api("/api/reports");
 let vals=r.daily_sales.slice().reverse(),max=Math.max(1,...vals.map(x=>x.total));
 $("#content").innerHTML=`
 <section class="shop-hero">
   <div class="hero-row">
     <div>
       <span class="shop-badge">⚕ TRUSTED PHARMACY MANAGEMENT</span>
       <h1>Welcome to Health Medicines</h1>
       <p>Professional medicine, inventory & billing management dashboard.</p>
       <p>Our goal is to keep your pharmacy organized, your stock accurate and your billing simple.</p>
     </div>
     <div style="font-size:64px">💊</div>
   </div>
 </section>

 <div class="shop-info-grid">
   <div class="info-tile"><div class="info-icon">📍</div><div><b>Shop Location</b><span>Newasa Road, Shrirampur<br>Near Alpha Hospital</span></div></div>
   <div class="info-tile"><div class="info-icon">🕒</div><div><b>Store Operations</b><span>Medicine stock • Billing • Purchases • Reports</span></div></div>
   <div class="info-tile"><div class="info-icon">🛡️</div><div><b>Smart Stock Control</b><span>Expiry, low-stock and batch tracking in one place.</span></div></div>
 </div>

 <div class="cards">
 ${card("Medicines",d.medicines,"accent")}
 ${card("Total Stock",d.stock,"success")}
 ${card("Low Stock",d.low_stock,"warn")}
 ${card("Out of Stock",d.out_of_stock,"danger")}
 ${card("Expired",d.expired,"danger")}
 ${card("Expiring ≤30d",d.expiring_soon,"warn")}
 ${card("Today's Sales",money(d.today_sales),"accent")}
 ${card("Today's Profit",money(d.today_profit),"success")}
 </div>

 <div class="panel" style="margin-top:16px">
   <h3>⚡ Quick Actions</h3>
   <div class="quick-grid">
     <button class="quick-btn" onclick="show('pos')">🧾 New Sale<small>Create a customer bill</small></button>
     <button class="quick-btn" onclick="show('purchase')">📦 Add New Stock<small>Record purchase/inward stock</small></button>
     <button class="quick-btn" onclick="show('medicines')">💊 Medicines<small>Manage medicine master</small></button>
     <button class="quick-btn" onclick="show('expiry')">⏱ Expiry Check<small>Check 30/60/90 day expiry</small></button>
   </div>
 </div>

 <div class="grid2">
   <div class="panel"><h3>📈 Sales — Last 31 Days</h3>
     <div class="chart">${vals.map(x=>`<div class="bar" title="${money(x.total)}" style="height:${Math.max(8,x.total/max*150)}px"><span>${x.day.slice(5)}</span></div>`).join("")}</div>
   </div>
   <div class="panel">
     <h3>🏪 Health Medicines Summary</h3>
     <p class="muted">Today's new stock: <b>${d.new_stock}</b> units</p>
     <p class="muted">Today's purchase: <b>${money(d.today_purchase)}</b></p>
     <p class="muted">Stock valuation: <b>${money(r.stock_valuation)}</b></p>
     <p class="muted">Location: <b>Newasa Road, Shrirampur</b></p>
     <p class="muted">Landmark: <b>Near Alpha Hospital</b></p>
   </div>
 </div>`;
}
function card(l,v,c){return `<div class="card ${c}"><div class="label">${l}</div><div class="value">${v}</div></div>`}
async function medicinePage(){medicines=await api("/api/medicines");$("#content").innerHTML=`<div class="toolbar"><input id="medQ" placeholder="Search medicine..."><button class="btn primary" onclick="medicineForm()">+ Add Medicine</button></div><div class="panel">${table(medicines,[["code","Code"],["name","Medicine"],["generic_name","Generic"],["manufacturer","Manufacturer"],["category","Category"],["stock","Stock"],["next_expiry","Next Expiry"]])}</div>`;$("#medQ").oninput=async e=>{medicines=await api("/api/medicines?q="+encodeURIComponent(e.target.value));$(".panel").innerHTML=table(medicines,[["code","Code"],["name","Medicine"],["generic_name","Generic"],["manufacturer","Manufacturer"],["category","Category"],["stock","Stock"],["next_expiry","Next Expiry"]])}}
function medicineForm(){modal(`<h3>Add Medicine</h3><form id="mf" class="form">${["code","name","generic_name","manufacturer","category","form","mrp","purchase_price","selling_price","gst","min_stock","storage"].map(x=>`<input name="${x}" placeholder="${x.replaceAll("_"," ")}" ${["code","name","mrp","selling_price","gst","min_stock"].includes(x)?"required":""}>`).join("")}<button class="btn primary">Save Medicine</button></form>`);$("#mf").onsubmit=async e=>{e.preventDefault();let o=Object.fromEntries(new FormData(e.target));try{await api("/api/medicines",{method:"POST",body:JSON.stringify(o)});closeModal();toast("Medicine saved");medicinePage()}catch(e){toast(e.message)}}}
async function stockPage(){let d=await api("/api/stock");$("#content").innerHTML=`<div class="panel"><div class="toolbar"><button class="btn" onclick="show('expiry')">Expiry Control</button></div>${table(d,[["code","Code"],["name","Medicine"],["batch_no","Batch"],["quantity","Qty"],["purchase_price","Purchase"],["mrp","MRP"],["expiry_date","Expiry"],["status","Status"]])}</div>`}
async function expiryPage(){let d=await api("/api/expiry?days=90");$("#content").innerHTML=`<div class="toolbar"><button class="btn" onclick="expiryDays(30)">30 Days</button><button class="btn" onclick="expiryDays(60)">60 Days</button><button class="btn" onclick="expiryDays(90)">90 Days</button></div><div class="panel">${table(d,[["code","Code"],["name","Medicine"],["batch_no","Batch"],["quantity","Qty"],["expiry_date","Expiry"],["status","Status"]])}</div>`}
async function expiryDays(n){let d=await api("/api/expiry?days="+n);$(".panel").innerHTML=table(d,[["code","Code"],["name","Medicine"],["batch_no","Batch"],["quantity","Qty"],["expiry_date","Expiry"],["status","Status"]])}
async function purchasePage(){let ms=await api("/api/medicines"),ss=await api("/api/suppliers");$("#content").innerHTML=`<div class="panel"><h3>New Stock / Purchase</h3><form id="pf" class="form"><input name="invoice_no" placeholder="Supplier invoice no."><select name="supplier_id">${ss.map(s=>`<option value="${s.id}">${s.name}</option>`).join("")}</select><div class="full"><table class="table" id="pi"><tr><th>Medicine</th><th>Batch</th><th>Qty</th><th>Purchase Price</th><th>MRP</th><th>Expiry</th><th></th></tr></table><button type="button" class="btn" onclick="addPurchaseRow()">+ Add item</button></div><button class="btn primary">Save Purchase</button></form></div>`;window.pm=ms;addPurchaseRow();$("#pf").onsubmit=async e=>{e.preventDefault();let items=[...$("#pi").querySelectorAll("tr.item")].map(r=>Object.fromEntries([...r.querySelectorAll("[name]")].map(x=>[x.name,x.value])));try{let d=await api("/api/purchases",{method:"POST",body:JSON.stringify({invoice_no:e.target.invoice_no.value,supplier_id:e.target.supplier_id.value,items})});toast("Purchase saved: "+money(d.grand_total));show("stock")}catch(e){toast(e.message)}}}
function addPurchaseRow(){let r=document.createElement("tr");r.className="item";r.innerHTML=`<td><select name="medicine_id">${pm.map(m=>`<option value="${m.id}">${m.name}</option>`).join("")}</select></td><td><input name="batch_no" required></td><td><input name="quantity" type="number" value="1" min="1"></td><td><input name="purchase_price" type="number" step=".01" value="0"></td><td><input name="mrp" type="number" step=".01" value="0"></td><td><input name="expiry_date" type="date" required></td><td><button type="button" class="btn" onclick="this.closest('tr').remove()">×</button></td>`;$("#pi").appendChild(r)}
async function posPage(){let ms=await api("/api/medicines"),cs=await api("/api/customers");window.posmed=ms;$("#content").innerHTML=`<div class="grid2"><div class="panel"><h3>Medicine Search</h3><input id="posq" placeholder="Search name/code..." style="width:100%;padding:12px;border:1px solid #ddd;border-radius:9px"><div id="posresults"></div></div><div class="panel"><h3>Current Bill</h3><div id="cart"></div><select id="customer"><option value="">Walk-in Customer</option>${cs.map(c=>`<option value="${c.id}">${c.name} — ${c.mobile||""}</option>`).join("")}</select><select id="payment"><option>CASH</option><option>UPI</option><option>CARD</option></select><h2 id="grand">₹0.00</h2><button class="btn primary" onclick="checkout()">Generate & Save Bill</button></div></div>`;renderPosResults(ms)}
function renderPosResults(ms){let arr=ms.slice(0,20);$("#posresults").innerHTML=table(arr,[["code","Code"],["name","Medicine"],["stock","Stock"]]);[...$("#posresults").querySelectorAll("tbody tr")].forEach((tr,i)=>{tr.onclick=()=>selectMed(arr[i]);tr.style.cursor="pointer"})}
$("#content").onclick=e=>{if(e.target.closest("#posresults tbody tr")){}}
async function selectMed(m){let bs=await api("/api/batches/"+m.id);let valid=bs.find(b=>b.quantity>0&&b.status!=="EXPIRED");if(!valid)return toast("No valid stock available");let found=cart.find(x=>x.batch_id===valid.id);if(found)found.quantity++;else cart.push({batch_id:valid.id,medicine_id:m.id,name:m.name,batch_no:valid.batch_no,expiry_date:valid.expiry_date,quantity:1,selling_price:valid.selling_price,purchase_price:valid.purchase_price,discount:0,gst_amount:0});renderCart()}
function renderCart(){if(!$("#cart"))return;$("#cart").innerHTML=cart.map((x,i)=>`<div style="padding:9px 0;border-bottom:1px solid #eee"><b>${x.name}</b><small> Batch ${x.batch_no}</small><div><input type="number" min="1" value="${x.quantity}" onchange="cart[${i}].quantity=+this.value;renderCart()"> × ${money(x.selling_price)} <button class="btn" onclick="cart.splice(${i},1);renderCart()">×</button></div></div>`).join("");let total=cart.reduce((s,x)=>s+x.quantity*x.selling_price-x.discount+x.gst_amount,0);$("#grand").textContent=money(total)}
async function checkout(){if(!cart.length)return toast("Cart is empty");try{let d=await api("/api/sales",{method:"POST",body:JSON.stringify({customer_id:$("#customer").value||null,payment_method:$("#payment").value,items:cart})});toast("Bill generated "+d.bill_no);cart=[];renderCart();await show("sales")}catch(e){toast(e.message)}}
async function salesPage(){let d=await api("/api/sales");$("#content").innerHTML=`<div class="toolbar"><button class="btn primary" onclick="show('pos')">+ New Bill</button><a class="btn" href="/api/reports/export.csv">Export CSV</a></div><div class="panel">${table(d,[["bill_no","Bill"],["sale_date","Date"],["customer","Customer"],["grand_total","Amount"],["payment_method","Payment"]])}</div>`}
async function purchasesPage(){let d=await api("/api/purchases");$("#content").innerHTML=`<div class="panel">${table(d,[["invoice_no","Invoice"],["purchase_date","Date"],["supplier","Supplier"],["grand_total","Amount"],["payment_status","Status"]])}</div>`}
async function customerPage(){let d=await api("/api/customers");$("#content").innerHTML=`<div class="toolbar"><button class="btn primary" onclick="customerForm()">+ Customer</button></div><div class="panel">${table(d,[["name","Name"],["mobile","Mobile"],["visits","Bills"],["total_purchases","Total Purchases"]])}</div>`}
function customerForm(){modal(`<h3>Add Customer</h3><form id="cf" class="form"><input name="name" placeholder="Name" required><input name="mobile" placeholder="Mobile"><input class="full" name="address" placeholder="Address"><button class="btn primary">Save</button></form>`);$("#cf").onsubmit=async e=>{e.preventDefault();await api("/api/customers",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});closeModal();customerPage()}}
async function supplierPage(){let d=await api("/api/suppliers");$("#content").innerHTML=`<div class="toolbar">${user.role==="ADMIN"?'<button class="btn primary" onclick="supplierForm()">+ Supplier</button>':""}</div><div class="panel">${table(d,[["name","Name"],["company","Company"],["phone","Phone"],["purchases","Purchases"],["total_purchases","Total"] ,["pending_payment","Pending"]])}</div>`}
function supplierForm(){modal(`<h3>Add Supplier</h3><form id="sf" class="form">${["name","company","phone","email","address","gst_number","pending_payment"].map(x=>`<input name="${x}" placeholder="${x.replaceAll("_"," ")}">`).join("")}<button class="btn primary">Save</button></form>`);$("#sf").onsubmit=async e=>{e.preventDefault();await api("/api/suppliers",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});closeModal();supplierPage()}}
async function reportsPage(){let d=await api("/api/reports");$("#content").innerHTML=`<div class="cards">${card("Total Profit",money(d.total_profit),"success")}${card("Stock Valuation",money(d.stock_valuation),"accent")}</div><div class="panel" style="margin-top:16px"><h3>Daily Sales</h3>${table(d.daily_sales,[["day","Date"],["bills","Bills"],["total","Sales"]])}</div>`}
async function settingsPage(){let d=await api("/api/settings");$("#content").innerHTML=`<div class="panel"><h3>Shop / Invoice Settings</h3><form id="set" class="form">${["shop_name","address","phone","email","gst_number","invoice_footer"].map(x=>`<input name="${x}" value="${d[x]||""}" placeholder="${x.replaceAll("_"," ")}">`).join("")}<button class="btn primary">Save Settings</button></form></div>`;$("#set").onsubmit=async e=>{e.preventDefault();await api("/api/settings",{method:"PUT",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});toast("Settings saved")}}
function modal(html){let d=document.createElement("div");d.className="modal";d.id="modal";d.innerHTML="<div>"+html+'<button class="btn right" onclick="closeModal()">Close</button></div>';document.body.appendChild(d)}
function closeModal(){$("#modal")?.remove()}
