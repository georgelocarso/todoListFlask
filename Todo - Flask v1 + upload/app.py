from flask import Flask,render_template,request,redirect,url_for,session,make_response
import sqlite3
import json
import pdfkit
import os
import os.path
from werkzeug.utils import secure_filename
application =Flask(__name__)
application.secret_key = "super secret key"
application.config['UPLOAD_FOLDER'] = os.path.realpath('.') + '/static/upload'
application.config['MAX_CONTENT_PATH'] = 10000000
#https://docs.python.org/3/library/sqlite3.html <-- sumber referensi untuk sqlite


def setup():
    conn_setup = sqlite3.connect('database.db')
    cursor_setup=conn_setup.cursor()
    cursor_setup.execute('''CREATE TABLE IF NOT EXISTS user(username text, password text)''')
    cursor_setup.execute('''CREATE TABLE IF NOT EXISTS todo_item(username text ,item text)''')  
    conn_setup.commit()
    conn_setup.close()
 
setup()

path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)


application.config['PDF_FOLDER'] = os.path.realpath('.') + \
   '/static/pdf'
application.config['TEMPLATE_FOLDER'] = os.path.realpath('.') + \
   '/templates'

conn=cursor=None
def openDB():
    global conn,cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
def closeDB():
    global conn,cursor
    conn.commit()
    cursor.close()
    conn.close()

#login page
@application.route('/', methods=['GET', 'POST'])
def index():
    if "username" in session:
        return redirect(url_for("home"))
    else :
        error = None
        if request.method == 'POST':
            uname = request.form['username']
            password = request.form['password']
            #ambil data dalam db
            openDB()
            rows = cursor.execute('SELECT * FROM user where username=? AND password=?', (uname,password))
            rows = rows.fetchall()
            container = []
            if len(rows) == 1:
                session["username"] = uname
                return redirect(url_for('home'))
            else:
                error = 'Invalid Credentials. Please try again.'
        return render_template('login.html', error=error)

@application.route('/home',methods=['GET', 'POST'])    
def home():    
    # return f"<h1>{username_getFromsession}</h1>"

    if "username" in session:
        username_getFromsession = session["username"]
        return render_template("home.html",uname_from_flask=username_getFromsession)
    else : 
        return redirect(url_for("index"))

@application.route('/logout')    
def logout():    
        session.pop("username",None)
        return redirect(url_for("index"))


#register page
@application.route('/register', methods=['GET','POST'])
def register():
    if "username" in session:
        return redirect(url_for("home"))
    else :
        if request.method == 'POST':
            uname = request.form['uname']
            pw = request.form['pass']
            re_pw = request.form['repass']
            if (pw == re_pw) :
                data = uname, pw
                #cek apakah sudah ada username yang sama
                openDB()
                rows = cursor.execute('SELECT * FROM user where username=?', (uname,))
                rows = rows.fetchall()
                container = []
                if len(rows) == 0:
                #
                    openDB()
                    cursor.execute('INSERT INTO user VALUES(?,?)',data)
                    conn.commit()
                    closeDB()
                    pesan = "Account Registered, Please go to Login Page"
                    return render_template('register.html', pesan=pesan)
                else:
                    error = 'Username sudah terpakai, harap ganti yang lain.'
                    return render_template('register.html', error = error)
            else :
                error = 'Password Not Matched, Plesae Try Again'
                return render_template('register.html', error = error)
        return render_template('register.html')

@application.route('/profile', methods=['GET','POST'])
def profile():
	username_getFromsession = session["username"]
	
	if os.path.isfile('static/upload/'+username_getFromsession+'.jpg'):
		imgName = username_getFromsession+".jpg"
	else:
		imgName = "default_image.png"
	
	return render_template('profile.html',uname_from_flask=username_getFromsession,imgName=imgName)
    
    
#mulai kebawah memakai model api
@application.route('/getTask', methods=['GET'])    
def getTask():    
    openDB()
    t = (request.args.get('username'),)
    cursor.execute("SELECT rowid,item FROM todo_item where username=?",t)
    data=cursor.fetchall()
    closeDB()
    return json.dumps(data)
    
@application.route('/updateTask', methods=['GET'])    
def updateTask():
    try:
        openDB()
        t = (request.args.get('newTask'),request.args.get('index'), )
        cursor.execute("UPDATE todo_item SET item=? WHERE rowid=?",t)
        closeDB()
        return "success"
    except sqlite3.Error as er:
        return json.dumps("failed")
    
@application.route('/deleteTask', methods=['GET'])    
def deleteTask():    
    try:
        openDB()
        t = (request.args.get('index'),)
        cursor.execute("DELETE FROM todo_item where rowid=?",t)
        closeDB()
        return "success"
    except sqlite3.Error as er:
        return json.dumps("failed")
    
@application.route('/deleteAllTask', methods=['GET'])    
def deleteAllTask():    
    try:
        openDB()
        #https://www.tutorialspoint.com/sqlite/sqlite_truncate_table.htm <-- sumber referensi truncate table
        cursor.execute("DELETE FROM todo_item")
        closeDB()
        return "success"
    except sqlite3.Error as er:
        return json.dumps("failed")
    
@application.route('/newTask', methods=['GET'])    
def newTask():
    try:
        openDB()
        #https://stackoverflow.com/questions/16856647/sqlite3-programmingerror-incorrect-number-of-bindings-supplied-the-current-sta <-- sumber referensi untuk error di sqlite3
        #harus di kasih koma di akhir biar tuppels
        t = (request.args.get('username'), request.args.get('newTask'),)
        cursor.execute("INSERT INTO todo_item VALUES (?,?)", t)
        closeDB()
        return "success"
    except sqlite3.Error as er:
        return json.dumps("failed")

@application.route('/print', methods=['GET'])          
def print():
    openDB()
    #t = (request.args.get('username'),)
    cursor.execute("SELECT item FROM todo_item where username='steven'")
    data=cursor.fetchall()
    closeDB()
    rendered = render_template('print.html',data=data)
    pdf = pdfkit.from_string(rendered, False, configuration=config)
    #return "Proses konversi ke PDF telah berhasil dilakukan.<br />Klik<a href='http://localhost:5000/static/pdf/pdftodo.pdf'>di sini</a> "
    
    response=make_response(pdf)
    response.headers['Content-Type']='application/pdf'
    response.headers['Content-Disposition']='inline; filename=output.pdf'
    return response;
	
@application.route('/upload', methods=['GET','POST'])
def upload():
	if request.method == 'POST':
		f	= request.files['file']
		username_getFromsession = session["username"]
		f.filename = username_getFromsession+".jpg"
		filename = application.config['UPLOAD_FOLDER'] + '/' + secure_filename(f.filename)
		try:
			f.save(filename)
			return render_template('upload_sukses.html', filename=secure_filename(f.filename))
		except:
			return render_template('upload_gagal.html', filename=secure_filename(f.filename))
	return render_template('form.html')
    
if __name__ == '__main__':
    application.run(debug=True)
