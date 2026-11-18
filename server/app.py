import os, secrets, sqlite3, time, hashlib, math
from functools import wraps
from flask import Flask, g, jsonify, request, render_template, session, redirect, url_for
from werkzeug.security import check_password_hash
app=Flask(__name__); app.secret_key=os.environ.get('SESSION_SECRET') or secrets.token_hex(32); DB=os.environ.get('DATABASE_PATH','family_guardian.sqlite3')
@app.after_request
def disable_browser_cache(response):
    response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma']='no-cache'
    response.headers['Expires']='0'
    return response
def db():
    if 'db' not in g: g.db=sqlite3.connect(DB); g.db.row_factory=sqlite3.Row; g.db.execute('PRAGMA foreign_keys=ON')
    return g.db
@app.teardown_appcontext
def close_db(error):
    c=g.pop('db',None)
    if c:c.close()
def init_db():
    with app.app_context(): db().executescript('''CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,name TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,created INTEGER NOT NULL,last_seen INTEGER); CREATE TABLE IF NOT EXISTS locations(id INTEGER PRIMARY KEY,device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,lat REAL NOT NULL,lon REAL NOT NULL,accuracy REAL,battery INTEGER,created INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS pairing_codes(code_hash TEXT PRIMARY KEY,expires INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS zones(id INTEGER PRIMARY KEY,name TEXT NOT NULL,lat REAL NOT NULL,lon REAL NOT NULL,radius REAL NOT NULL); CREATE TABLE IF NOT EXISTS zone_state(device_id TEXT NOT NULL,zone_id INTEGER NOT NULL,inside INTEGER NOT NULL,PRIMARY KEY(device_id,zone_id)); CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,device_id TEXT NOT NULL,device_name TEXT NOT NULL,zone_name TEXT NOT NULL,event TEXT NOT NULL,created INTEGER NOT NULL);''')
def parent(f):
    @wraps(f)
    def inner(*a,**kw):
        if not session.get('parent'):return redirect(url_for('login'))
        return f(*a,**kw)
    return inner
def device_auth(f):
    @wraps(f)
    def inner(*a,**kw):
        token=request.headers.get('Authorization','').removeprefix('Bearer ').strip()
        row=db().execute('SELECT id FROM devices WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone() if token else None
        if not row:return jsonify(error='Invalid or missing device token'),401
        g.device_id=row['id'];return f(*a,**kw)
    return inner
@app.get('/login')
def login():return render_template('login.html',error=None)
@app.post('/login')
def login_post():
    user=os.environ.get('PARENT_USERNAME'); pw=os.environ.get('PARENT_PASSWORD_HASH')
    if not user or not pw:return render_template('login.html',error='Configure PARENT_USERNAME and PARENT_PASSWORD_HASH.'),503
    if secrets.compare_digest(request.form.get('username',''),user) and check_password_hash(pw,request.form.get('password','')):session.clear();session['parent']=True;return redirect('/')
    return render_template('login.html',error='Login failed.'),401
@app.post('/logout')
def logout():session.clear();return redirect('/login')
@app.get('/')
@parent
def dashboard():return render_template('dashboard.html')
@app.get('/api/dashboard')
@parent
def dashboard_data():
    ds=db().execute('SELECT d.id,d.name,d.created,d.last_seen,l.lat,l.lon,l.accuracy,l.battery,l.created updated FROM devices d LEFT JOIN locations l ON l.id=(SELECT id FROM locations WHERE device_id=d.id ORDER BY created DESC LIMIT 1) ORDER BY d.created DESC').fetchall()
    alerts=db().execute('SELECT * FROM alerts ORDER BY created DESC LIMIT 20').fetchall()
    return jsonify(devices=[dict(x,connected=bool(x['last_seen'] and time.time()-x['last_seen']<180)) for x in ds],zones=[dict(x) for x in db().execute('SELECT * FROM zones')],alerts=[dict(x) for x in alerts])
@app.post('/api/pairing-codes')
@parent
def new_code():
    raw=secrets.token_urlsafe(9);db().execute('INSERT INTO pairing_codes VALUES(?,?,0)',(hashlib.sha256(raw.encode()).hexdigest(),int(time.time())+600));db().commit();return jsonify(code=raw,expires_in=600)
@app.post('/api/devices/register')
def register():
    j=request.get_json(silent=True) or {};code=str(j.get('pairing_code','')).strip();name=str(j.get('name','')).strip()[:80]
    if not code or not name:return jsonify(error='Pairing code and device name are required'),400
    h=hashlib.sha256(code.encode()).hexdigest();row=db().execute('SELECT * FROM pairing_codes WHERE code_hash=? AND used=0 AND expires>?',(h,int(time.time()))).fetchone()
    if not row:return jsonify(error='Pairing code is invalid or expired'),403
    token=secrets.token_urlsafe(32);did=secrets.token_hex(8);c=db();c.execute('UPDATE pairing_codes SET used=1 WHERE code_hash=?',(h,));c.execute('INSERT INTO devices VALUES(?,?,?,?,?)',(did,name,hashlib.sha256(token.encode()).hexdigest(),int(time.time()),int(time.time())));c.commit();return jsonify(device_id=did,device_token=token),201
@app.post('/api/locations')
@device_auth
def add_location():
    j=request.get_json(silent=True) or {}
    try:lat=float(j['latitude']);lon=float(j['longitude']);acc=float(j.get('accuracy') or 0);bat=int(j['battery']) if j.get('battery') is not None else None
    except (KeyError,TypeError,ValueError):return jsonify(error='Valid coordinates required'),400
    if not(-90<=lat<=90 and -180<=lon<=180 and 0<=acc<=100000 and (bat is None or 0<=bat<=100)):return jsonify(error='Values out of range'),400
    c=db();now=int(time.time());c.execute('INSERT INTO locations(device_id,lat,lon,accuracy,battery,created) VALUES(?,?,?,?,?,?)',(g.device_id,lat,lon,acc,bat,now));c.execute('UPDATE devices SET last_seen=? WHERE id=?',(now,g.device_id))
    device=c.execute('SELECT name FROM devices WHERE id=?',(g.device_id,)).fetchone()['name']
    for z in c.execute('SELECT * FROM zones').fetchall():
        p1,p2=math.radians(lat),math.radians(z['lat']);dp=math.radians(z['lat']-lat);dl=math.radians(z['lon']-lon);a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2;inside=int(6371000*2*math.atan2(math.sqrt(a),math.sqrt(1-a))<=z['radius'])
        old=c.execute('SELECT inside FROM zone_state WHERE device_id=? AND zone_id=?',(g.device_id,z['id'])).fetchone()
        if old and old['inside']!=inside:c.execute('INSERT INTO alerts(device_id,device_name,zone_name,event,created) VALUES(?,?,?,?,?)',(g.device_id,device,z['name'],'arrived' if inside else 'left',now))
        c.execute('INSERT INTO zone_state VALUES(?,?,?) ON CONFLICT(device_id,zone_id) DO UPDATE SET inside=excluded.inside',(g.device_id,z['id'],inside))
    c.commit();return jsonify(ok=True,received_at=now)
@app.get('/api/devices/<device_id>/history')
@parent
def history(device_id):
    limit=min(max(request.args.get('limit',100,type=int),1),1000);rows=db().execute('SELECT lat,lon,accuracy,battery,created FROM locations WHERE device_id=? ORDER BY created DESC LIMIT ?',(device_id,limit)).fetchall();return jsonify(points=[dict(r) for r in rows])
@app.post('/api/zones')
@parent
def add_zone():
    j=request.get_json(silent=True) or {}
    try:name=str(j['name']).strip()[:60];lat=float(j['latitude']);lon=float(j['longitude']);radius=float(j['radius_m'])
    except (KeyError,TypeError,ValueError):return jsonify(error='Name, coordinates, and radius required'),400
    if not name or not(-90<=lat<=90 and -180<=lon<=180 and 25<=radius<=10000):return jsonify(error='Zone values out of range'),400
    cur=db().execute('INSERT INTO zones(name,lat,lon,radius) VALUES(?,?,?,?)',(name,lat,lon,radius));db().commit();return jsonify(id=cur.lastrowid),201
@app.delete('/api/zones/<int:zone_id>')
@parent
def delete_zone(zone_id):db().execute('DELETE FROM zones WHERE id=?',(zone_id,));db().commit();return jsonify(ok=True)
init_db()
if __name__=='__main__':app.run(host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','5000')),debug=False)
