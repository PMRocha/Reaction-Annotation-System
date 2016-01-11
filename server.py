from flask import Flask, make_response, request, current_app, Response, render_template, send_from_directory, redirect, url_for, flash
from flask.ext.login import LoginManager, login_required, login_user, logout_user, current_user
from flask_bootstrap import Bootstrap
from werkzeug import secure_filename
import MySQLdb
import solr
import unicodedata
import codecs
import os
import sys
from datetime import timedelta
import datetime
import hashlib
import subprocess
from functools import update_wrapper
import json
from random import shuffle
from passlib.hash import sha256_crypt
from functools import wraps
#from werkzeug.debug import DebuggedApplication
import math
import random
import collections
import smtplib
from email.mime.text import MIMEText
import nltk

print >> sys.stderr, "start"
db = MySQLdb.connect(host="localhost", # your host, usually localhost
                     user="ssim_annotation", # your username
                     passwd="ssim_annotation_pass", # your password
                     db="ssim_annotation") # name of the data base
db.autocommit(True)

UPLOAD_FOLDER = "/home/ssim_annotation/Reaction-Annotation-System/uploads/" #'C:\Python27\\annotationSystem\uploads'
ALLOWED_EXTENSIONS = set(['R','py'])
ALLOWED_EXTENSIONS1 = set(['csv'])

SOLR_PATH = "/portugal/tweets/" #"/portugal/tweets/"
SOLR_HOST = "reaction.fe.up.pt" #"reaction.fe.up.pt"
SOLR_HTTP = "http://" + SOLR_HOST + SOLR_PATH
SOLR_USER = "popstar_pedrosaleiro"
SOLR_PASS = "p3dr0@2013!"
SOLR_QUERY_SIZE = 10000

s = solr.SolrConnection(SOLR_HTTP, http_user = SOLR_USER, http_pass= SOLR_PASS)
print >> sys.stderr, s
#subprocess that schedulles the annotations
#subprocess.Popen('python annotationSystem/runningScript.py', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

class User:

    def __init__(self, id, name, email, password, role, active, ratio):
        self.email = email
        self.password = password
        self.name = name
        self.id = id
        self.role = role
        self.active = active
        self.ratio = ratio



    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def get_role(self):
        return self.role

    def __repr__(self):
        return '<User %r>' % (self.name)

class Label:
	
	def __init__(self,id,name,description):
		self.id=id
		self.name=name
		self.description=description

class OneShotUser:

    def __init__(self, id, occupied, idCampaign, ratio):
        self.id = id
        self.occupied = occupied
        self.idCampaign = idCampaign
        self.ratio = ratio

class Script:
    def __init__(self, id, name, filepath, filename):
        self.name = name
        self.id = id
        self.filepath = filepath
        self.filename = filename

class Campaign:
    def __init__(self, id, name, startDate, endDate, period, deltaTime, idScript,numberAnnotations, closed,total,ratio):
        self.name = name
        self.id = id
        self.startDate = startDate
        self.endDate = endDate
        self.period = period
        self.deltaTime = deltaTime
        self.idScript = idScript
        self.closed=closed
        self.total=total
        self.ratio=ratio
        self.numberAnnotations = numberAnnotations

class Run:
    def __init__(self, id, startDate, endDate, solrQuery, closed,total,ratio):
        self.id = id
        self.startDate = startDate
        self.endDate = endDate
        self.closed=closed
        self.total=total
        self.ratio=ratio
        self.solrQuery = solrQuery
        
class Agreement:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Annotation:
    def __init__(self, result, idUser, idTweet, idRun, annotationDate, polarity, isClosed,text, idCampaign, username, target):
        self.result = result
        self.idUser = idUser
        self.idTweet = idTweet
        self.idRun = idRun
        self.annotationDate = annotationDate
        self.polarity = polarity
        self.isClosed = isClosed
        self.text = text
        self.idCampaign = idCampaign
        self.username = username
        self.target = target

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def to_String(self):
        l = []
        l.append("{")
        l.append("result:")
        l.append(str(self.result))
        l.append(",idUser:")
        l.append(str(self.idUser))
        l.append(",idRun:")
        l.append(str(self.idRun))
        l.append(",idTweet:")
        l.append("'")
        l.append(str(self.idTweet))
        l.append("'")
        l.append("}")

        return ''.join(l)

class ClassificationLabel:
    def __init__(self, idLabel, nameLabel,descriptionLabel):
        self.id = idLabel
        self.name = nameLabel
        self.description = descriptionLabel


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

app = Flask(__name__, static_folder='static')
app.secret_key = 'why would I tell you my secret key?'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
lm = LoginManager()
lm.init_app(app)
Bootstrap(app)

@lm.user_loader
def load_user(userid):
    return check_db(userid)

def check_db(userid):
    idUser=0

    cur = db.cursor()
    command = "SELECT * FROM user where idUser=" + '"'+ userid + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

    if idUser == 0:
        return None
    else:
        user = User(unicode(idUser),fullname, email, password_codified, role, active,0)
        return user

def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.get_role() not in roles:
                flash("You do not have administrator permissions to access that page.","error")
                return redirect(url_for('profile'))
            return f(*args, **kwargs)
        return wrapped
    return wrapper

@app.route("/")
def hello():
    return render_template('index.html')

@app.route("/login", methods = ['GET'])
def login1():
    return render_template('login.html')

@app.route("/login", methods = ['POST'])
def login():
    print >> sys.stderr, "1"
    email = request.form['email']
    password = request.form['password']

    h = hashlib.new('ripemd160')
    h.update(password)
    encoded_password =  h.hexdigest()
    print >> sys.stderr, "2"

    idUser = 0
    cur = db.cursor()
    command = "SELECT * FROM user where email=" + '"'+ email + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

    if idUser == 0:
        flash("User not found.","error")
        return redirect(url_for('login'))

    if active == 0:
        flash("User is inactive. Please contact the administrator.","error")
        return redirect(url_for('login'))
    print >> sys.stderr, "3"
    user = User(unicode(idUser),fullname, email, password_codified, role, active,0)
    print >> sys.stderr, "4"
    load_user(user.id)
    print >> sys.stderr, "5"

    if user != None:
        print >> sys.stderr, "user found"
        if encoded_password == user.password:
            login_user(user)
            print >> sys.stderr, "user logged in"
            flash("Logged in successfully.","success")

            #print current_user.name
            print >> sys.stderr, "correct user"
            return redirect(url_for('profile'))
        else:
            flash("Wrong password.","error")
            print >> sys.stderr, "wrong user"
            return redirect(url_for('login'))
    else:
        flash("User not found.","error")
        print >> sys.stderr, "user not found"
        return redirect(url_for('login'))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.","success")
    return redirect(url_for('hello'))

@app.route("/profile")
@login_required
def profile():
    campaigns = []
    cur = db.cursor()
    command = "SELECT * FROM campaign where idCampaign in (select idCampaign from campaign_users where idUser = " + str(current_user.id) +");"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]
        deltaTime = row[5]
        idScript = row[6]
        #print >> sys.stderr, idCampaign

        closed=0
        cur1 = db.cursor()
        command = "select count(*) from annotation where annotation.isClosed = 1 and annotation.idUser =" + str(current_user.id) + " and annotation.idRun in ( select idRun from run where idCampaign=" + str(idCampaign) + ");"
        cur1.execute(command)
        for row in cur1.fetchall():
            closed=row[0]
        #print >> sys.stderr, closed
        total=0
        cur1 = db.cursor()
        command = "select count(*) from annotation where annotation.idUser =" + str(current_user.id) + " and annotation.idRun in ( select idRun from run where idCampaign=" + str(idCampaign) + ");"
        cur1.execute(command)
        for row in cur1.fetchall():
            total=row[0]
        #print >> sys.stderr, total
        #print >> sys.stderr, "\n"
        if total != 0:    #campaigns that have already started
            ratio = round(float(closed)/float(total) * 100)
            #print >> sys.stderr, ratio
            campaign = Campaign(idCampaign, name, startDate, endDate, period, deltaTime, idScript,"",closed,total,ratio)
            campaigns.append(campaign)


    print >> sys.stderr, campaigns
    return render_template('profile.html',campaigns=campaigns) #, annotations=annotations)

@app.route("/addLabel", methods = ['GET'])
@login_required
@requires_roles('admin')
def addLabel():
    return render_template('addLabel.html')

@app.route("/addLabel", methods = ['POST'])
@login_required
@requires_roles('admin')
def addLabel1():

    label = request.form['label']
    description = request.form['description']

    cur = db.cursor()
    command = "SELECT count(*) FROM classification_label where name=" + '"'+ label + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        count = row[0]

    if count == 0:
        command = "insert into classification_label (name, description) values ("    + '"' + label + '"' + ","  + '"' + description + '"'");"
        cur.execute(command)
        db.commit()
        flash("New label added successfully.","success")
        return redirect(url_for('profile'))
    else:
        flash("Label is already defined.","error")
        return redirect(url_for('addUser'))

@app.route("/ListLabels", methods = ['GET'])
@login_required
@requires_roles('admin')
def listLabels():
    
    labels = []
    cur = db.cursor()
    command = "SELECT * FROM classification_label;"
    cur.execute(command)
    for row in cur.fetchall():
        idLabel = row[0]
        name = row[1]
        description = row[2]

        label = Label(unicode(idLabel),name, description)
        labels.append(label)

    return render_template('listLabels.html', labels=labels)

@app.route("/addUser", methods = ['GET'])
@login_required
@requires_roles('admin')
def addUser():
    return render_template('addUser.html')

@app.route("/addUser", methods = ['POST'])
@login_required
@requires_roles('admin')
def addUser1():
    isAdmin=False

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    h = hashlib.new('ripemd160')
    h.update(password)
    codified_password = h.hexdigest()

    if "isAdmin" in request.form:
        isAdmin=True

    admin = "0"
    if isAdmin:
        admin = "1"
    active="1"


    cur = db.cursor()
    command = "SELECT count(*) FROM user where email=" + '"'+ email + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        count = row[0]

    if count == 0:
        command = "insert into user (fullname, email, password_codified, isActive, isAdmin) values ("    + '"' + name + '"' + ","  + '"' + email + '"' + ","    + '"' + codified_password + '"' + ","    + active + "," + admin + ");"
        cur.execute(command)
        db.commit()
        flash("New user added successfully.","success")
        sendOneEmail("Your account has been successfully registered in 192.168.102.190:3333.\n Please login to view pending annotations.", "New account", email)
        return redirect(url_for('profile'))
    else:
        flash("Email is already in use.","error")
        return redirect(url_for('addUser'))


@app.route("/addUsersCSV", methods = ['GET'])
@login_required
@requires_roles('admin')
def addUsersCSV():
    return render_template('addUsersCSV.html')

@app.route("/addUsersCSV", methods = ['POST'])
@login_required
@requires_roles('admin')
def addUsersCSV1():
    users = []
    file = request.files['file']
    if file and allowed_file1(file.filename):
        filename = secure_filename(file.filename)
        #print filename

        data = file.read()
        clean_data = data.split("\n")

        for user in clean_data:
            print >> sys.stderr, user
            count = user.count(";")
            print >> sys.stderr, count

            if count == 3:
                tmp = user[::-1].strip()[1:][::-1]
                user=tmp

            elif count > 3:
                flash("File is not compliant with the syntax.","error")
                return redirect(url_for('profile'))

            user_data = user.split(";")

            name = user_data[0].strip()
            email = user_data[1].strip()
            password = user_data[2].strip()

            #add users to db
            isAdmin=False
            h = hashlib.new('ripemd160')
            h.update(password)
            codified_password = h.hexdigest()

            if "isAdmin" in request.form:
                isAdmin=True

            admin = "0"
            if isAdmin:
                admin = "1"

            active="1"

            cur = db.cursor()
            command = "SELECT count(*) FROM user where email=" + '"'+ email + '"' + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count = row[0]

            if count == 0:
                command = "insert into user (fullname, email, password_codified, isActive, isAdmin) values ("    + '"' + name + '"' + ","  + '"' + email + '"' + ","    + '"' + codified_password + '"' + ","    + active + "," + admin + ");"
                cur.execute(command)
                sendOneEmail("Your account has been successfully registered in 192.168.102.190:3333.\n Please login to view pending annotations.", "New account", email)
                db.commit()
                users.append(name)
    db.commit()
    tmp = ""
    for name in users:
        tmp = tmp + name + ";"

    if tmp != "":
        flash("Users added: " + tmp,"success")
    else:
        flash("No users were added." ,"error")
    return redirect(url_for('profile'))

@app.route("/editUser", methods = ['GET'])
@login_required
def editUser():
    return render_template('editUser.html')

@app.route("/editUser", methods = ['POST'])
@login_required
def editUser1():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    h = hashlib.new('ripemd160')
    h.update(password)
    codified_password = h.hexdigest()

    #print name
    #print email
    #print password

    changes = []
    if name != current_user.name:
        changes.append("name")
    if email != current_user.email:
        changes.append("email")
    if codified_password != current_user.password and password != "":
        changes.append("password")

    #verify if email is repeated in database
    idUser = 0
    cur = db.cursor()
    command = "SELECT idUser FROM user where email=" + '"'+ email + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]

    #print idUser
    #print current_user.id

    if str(idUser) != str(current_user.id) and idUser != 0:
        flash("Email is already in use. No changes were made","error")
        return redirect(url_for('editUser'))

    for itm in changes:
        if itm == "name":
            cur = db.cursor()
            command = "UPDATE user SET user.fullname = " + '"' + name + '"' + " where idUser = " + current_user.id;
            cur.execute(command)
        if itm == "email":
            cur = db.cursor()
            command = "UPDATE user SET user.email = " + '"' + email + '"' + " where idUser = " + current_user.id;
            cur.execute(command)
        if itm == "password":
            cur = db.cursor()
            command = "UPDATE user SET user.password_codified = " + '"' + codified_password + '"' + " where idUser = " + current_user.id;
            cur.execute(command)
    db.commit()

    flash("All changes were saved.","success")
    return redirect(url_for('profile'))

@app.route("/changeUserStatus/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def changeUserStatus(id):
    cur = db.cursor()
    command = "SELECT * FROM user where iduser=" + id + ";"
    cur.execute(command)
    for row in cur.fetchall():
        active = row[4]

    if active == 1:
        new_status = "0"
    else:
        new_status = "1"

    cur = db.cursor()
    command = "UPDATE user SET user.isActive = " + new_status +" where idUser = " + id;
    cur.execute(command)
    db.commit()

    return redirect(url_for('listUsers'))

@app.route("/changeUserAdmin/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def changeUserAdmin(id):
    cur = db.cursor()
    command = "SELECT * FROM user where iduser=" + id + ";"
    cur.execute(command)
    for row in cur.fetchall():
        admin = row[5]


    if admin == 1:
        new_status = "0"
    else:
        new_status = "1"

    cur = db.cursor()
    command = "UPDATE user SET user.isAdmin = " + new_status +" where idUser = " + id;
    cur.execute(command)
    db.commit()

    return redirect(url_for('listUsers'))

@app.route("/ListUsers", methods = ['GET'])
@login_required
@requires_roles('admin')
def listUsers():
    #get users
    users = []
    cur = db.cursor()
    command = "SELECT * FROM user;"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

        user = User(unicode(idUser),fullname, email, password_codified, role, active,0)
        users.append(user)

    return render_template('listUsers.html', users=users)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def allowed_file1(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS1

@app.route("/addScript", methods = ['GET'])
@login_required
@requires_roles('admin')
def addScript():
    return render_template('addScript.html')

@app.route("/addScript", methods = ['POST'])
@login_required
@requires_roles('admin')
def addScript1():
    name = request.form['name']
    #print name

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        #print filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        #print "teste"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        filepath1 = MySQLdb.escape_string(filepath)
        #print filepath1

        cur = db.cursor()
        command = "insert into script (name, filepath) values ("    + '"' + name + '"' + ","  + '"' + filepath1 + '"' + ");"
        cur.execute(command)
        db.commit()

        flash("New script added successfully.","success")
        return redirect(url_for('profile'))

    flash("Script type is not supported.","error")
    return redirect(url_for('profile'))

@app.route("/ListScripts", methods = ['GET'])
@login_required
@requires_roles('admin')
def listScripts():
    #get scripts
    scripts = []
    cur = db.cursor()
    command = "SELECT * FROM script;"
    cur.execute(command)
    for row in cur.fetchall():
        idScript = row[0]
        name = row[1]
        filepath = row[2]
        filename = filepath.split("\\")[::-1][0]

        script = Script(idScript,name,filepath,filename)
        scripts.append(script)

    return render_template('listScripts.html', scripts=scripts)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename, as_attachment=True)

@app.route("/addCampaign", methods = ['GET'])
@login_required
@requires_roles('admin')
def addCampaign():
    #get dates for datetime pickers
    today = datetime.datetime.now()
    end = today + datetime.timedelta(days=7)

    #get scripts
    scripts = []
    cur = db.cursor()
    command = "SELECT * FROM script;"
    cur.execute(command)
    for row in cur.fetchall():
        idScript = row[0]
        name = row[1]
        filepath = row[2]

        script = Script(idScript,name,filepath,filepath)
        scripts.append(script)

    #get users
    users = []
    cur = db.cursor()
    command = "SELECT * FROM user where user.isActive=1;"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

        user = User(unicode(idUser),fullname, email, password_codified, role, active,0)
        users.append(user)

    #get labels
    labels = []
    cur = db.cursor()
    command = "SELECT * FROM classification_label"
    cur.execute(command)
    for row in cur.fetchall():
        idLabel = row[0]
        name = row[1]
        description = row[2]

        label = Label(unicode(idLabel),name, description)
        labels.append(label)

    #TODO: let admin define active labels for the new campaign

    return render_template('addCampaign.html',start_date=today, end_date=end, users = users, scripts = scripts, labels = labels)


# Using two-tuples to preserve order.
REPLACEMENTS = (
    # Nuke nasty control characters.
    ('\x00', ''), # Start of heading
    ('\x01', ''), # Start of heading
    ('\x02', ''), # Start of text
    ('\x03', ''), # End of text
    ('\x04', ''), # End of transmission
    ('\x05', ''), # Enquiry
    ('\x06', ''), # Acknowledge
    ('\x07', ''), # Ring terminal bell
    ('\x08', ''), # Backspace
    ('\x0b', ''), # Vertical tab
    ('\x0c', ''), # Form feed
    ('\x0e', ''), # Shift out
    ('\x0f', ''), # Shift in
    ('\x10', ''), # Data link escape
    ('\x11', ''), # Device control 1
    ('\x12', ''), # Device control 2
    ('\x13', ''), # Device control 3
    ('\x14', ''), # Device control 4
    ('\x15', ''), # Negative acknowledge
    ('\x16', ''), # Synchronous idle
    ('\x17', ''), # End of transmission block
    ('\x18', ''), # Cancel
    ('\x19', ''), # End of medium
    ('\x1a', ''), # Substitute character
    ('\x1b', ''), # Escape
    ('\x1c', ''), # File separator
    ('\x1d', ''), # Group separator
    ('\x1e', ''), # Record separator
    ('\x1f', ''), # Unit separator
)

def sanitize(data):
    fixed_string = data
    for bad, good in REPLACEMENTS:
        fixed_string = fixed_string.replace(bad, good)
    return fixed_string

@app.route("/addCampaign", methods = ['POST'])
@login_required
@requires_roles('admin')
def addCampaign1():
    #print request.form
    name = request.form['name']
    startDate = request.form['startDate']
    endDate = request.form['endDate']
    period = request.form['period']
    one_shot_users = request.form['one-shot']
    number_annotations = request.form['number_annotations']
    days = request.form['days']
    size = request.form['limitSolr']

    if size == "0":
        size = SOLR_QUERY_SIZE
	
    periodDays = 0
    if period == "Daily":
        periodDays= "1";
    elif period == "Weekly":
        periodDays = "7"
    else:
        periodDays = "30"


    selectedUsers = []
    selectedUsers = request.form.getlist('selectedUsers')
    
    selectedLabels = []
    selectedLabels = request.form.getlist('selectedLabels')

    selectedScript = ""
    if "selectedScripts" in request.form:
        selectedScript = request.form['selectedScripts']

    solrQuery = []
    solrQuery = request.form.getlist('solr')
    
    solrTarget = []
    solrTarget = request.form.getlist('target')
    
    cleanSolrQuery = []
    for query in solrQuery:
       cleanSolrQuery.append(sanitize(query))
       

    if name == "":
        flash("Name is missing.","error")
        return redirect(url_for('addCampaign'))
    if days == "":
        flash("Number of days to be evaluated are missing.","error")
    if one_shot_users == "":
        flash("Number of one shot users to be added is missing.","error")
        return redirect(url_for('addCampaign'))
    if selectedUsers == []:
        flash("No users were assigned to this campaign.","error")
        return redirect(url_for('addCampaign'))
    if selectedLabels == []:
        flash("No Labels were assigned to this campaign.","error")
        return redirect(url_for('addCampaign'))
    if selectedScript == "":
        flash("No script was assigned to this campaign.","error")
        return redirect(url_for('addCampaign'))

    for x in xrange(0,len(solrQuery)):
        if solrQuery[x]!=  cleanSolrQuery[x]:
            print >> sys.stderr,solrQuery[x]
            print >> sys.stderr,cleanSolrQuery[x]
            flash("Solr Query contains invalid characters.","error")
            return redirect(url_for('addCampaign'))
        if solrQuery[x] == "":
            flash("Solr Query is missing. If you do not know Solr syntax or do not wish to pre-filter any parameters, please insert: " + '"' + "*:*" + '"',"error")
            return redirect(url_for('addCampaign'))


    start = datetime.datetime.strptime(startDate, '%Y-%m-%d')
    end = datetime.datetime.strptime(endDate, '%Y-%m-%d')
    if end <= start:
        flash("End date is prior or equal to the Start Date.","error")
        return redirect(url_for('addCampaign'))

    periodValue = int(periodDays)
    if start + datetime.timedelta(days=periodValue) > end:
        flash("Period chosen is not within Start and End Dates interval.","error")
        return redirect(url_for('addCampaign'))

    cur = db.cursor()
    command = "insert into campaign (campaignName,startDate,endDate,periodOfEachRun,deltaTimeForQuery,idScript,numberAnnotations) values  (" +    '"' + name + '"' + ","  + '"' + startDate + '"'+ ","  + '"' + endDate + '"'  + "," + periodDays + "," + days + "," + selectedScript + ", " + number_annotations + ");"
    cur.execute(command)
    db.commit()
     
    print >> sys.stderr,"inserted into campaign"

    idCampaign = 0
    cur = db.cursor()
    command = "SELECT LAST_INSERT_ID();"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]

    print >> sys.stderr,"inserted into campaign"

    #add users
    for usr in selectedUsers:
        cur = db.cursor()
        command = "insert into campaign_users (idCampaign,idUser) values  (" + str(idCampaign) + "," +  str(usr) + ");"
        cur.execute(command)
        db.commit()

    print >> sys.stderr,"added Users"

    totalQuery=solrQuery[0]
    solrQuery.pop(0)
    for query in solrQuery:
        totalQuery = totalQuery + ";" + query
        
    print >> sys.stderr,totalQuery

    #create runs
    counter = start
    while counter < end:
        init = counter
        finish = init + datetime.timedelta(days=periodValue)


        if finish > end:
            break

        cur = db.cursor()
        command = "insert into run (initDate,endDate,idCampaign,solrQuery) values  (" + '"' + str(init) + '"' + "," + '"' + str(finish) + '"' + "," + str(idCampaign)+ "," + '"' + str(totalQuery) + '"'  + ");"
        cur.execute(command)
        db.commit()
        counter += datetime.timedelta(days=periodValue)

        idRun = 0
        cur = db.cursor()
        command = "SELECT LAST_INSERT_ID();"
        cur.execute(command)
        for row in cur.fetchall():
            idRun = row[0]
        print >> sys.stderr,"added Runs"
        #add one-shot users
        cnt = 0
        while cnt < int(one_shot_users):
            cur = db.cursor()
            command = "insert into one_shot_user (idRun) values  (" + str(idRun) + ");"
            cur.execute(command)
            db.commit()
            cnt = cnt + 1
        print >> sys.stderr,"added on shot Users"
    #associate all labels to campaign
    #TODO: change to selected labels defined by admin
    cur = db.cursor()
    for lbl in selectedLabels:
        command = "insert into campaign_classification_labels (idCampaign,idClassification_label) values  (" + str(idCampaign)+ "," + str(lbl) + ");"
        cur.execute(command)
    db.commit()

    #load campaign now
    print >> sys.stderr, "addedCampaign"
    startCampaign(str(idCampaign),size,solrTarget)

    #subprocess.Popen(['python', '/var/www/annotationSystem2/runningScript.py'])#, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    flash("New campaign added successfully.","success")
    return redirect(url_for('profile'))


def sendEmail(message, subject, users):
    print >> sys.stderr, "start sending email"
    for user in users:
		print >> sys.stderr, user.email
		sendOneEmail(message, subject,user.email)
        


def sendOneEmail(message, subject, email):
    print >> sys.stderr, "start sending email"
    print >> sys.stderr, email
    fromaddr = 'annotation.system@gmail.com'

    toaddrs  = email

    msg = "\r\n".join([
        "From: annotation.system@gmail.com",
        "To: " + email,
        "Subject: " + subject,
        "",
        message
    ])

    print >> sys.stderr, "message built"

    # Credentials (if needed)
    username = 'annotation.system'
    password = 'reaction2015'

    # The actual mail send
    print >> sys.stderr, "start sending email"
    server = smtplib.SMTP('smtp.gmail.com:587')
    print >> sys.stderr, "start smtp server connection"
    server.ehlo()
    server.starttls()
    print >> sys.stderr, "start tls"
    server.login(username,password)
    print >> sys.stderr, "login"
    server.sendmail(fromaddr, toaddrs, msg)
    print >> sys.stderr, "send email"
    server.close()
    print >> sys.stderr, "email sent"


def startCampaign(idCampaign,querySize,solrTarget):
    today = datetime.datetime.now()
    initDate = str(today).split(" ")[0]
    cur = db.cursor()
    run = Run(0,0,0,0,0,0,0)
    command = "SELECT * FROM ssim_annotation.run where initDate= " + '"' + initDate + '"' + " and status=" + '"' + "schedulled" + '"' + " and idCampaign = " + str(idCampaign) + ";"
    cur.execute(command)
    print >> sys.stderr, "1"
    
    for row in cur.fetchall():
        idRun = row[0]
        startDate = str(row[1]).split(" ")[0]
        endDate = str(row[2]).split(" ")[0]
        solrQuery = row[4]
        run = Run(idRun,startDate,endDate,solrQuery,0,0,0)
        
    print >> sys.stderr, "2"
    #get run's campaign
    campaigns = []
    cur = db.cursor()
    command = "SELECT * FROM ssim_annotation.campaign where idCampaign = " + str(idCampaign) + ";"
    cur.execute(command)

    print >> sys.stderr, "tweets selected"
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]

        periodDays = 0
        if period == 1:
            periodDays= "1 Week";
        elif period == 7:
            periodDays = "1 Week"
        else:
            periodDays = "1 Month"
        deltaTime = row[5]
        idScript = row[6]
        numberAnnotations = row[7]
		
		
		
        campaign = Campaign(idCampaign, name, startDate, endDate, periodDays, deltaTime, idScript,numberAnnotations, 0,0,0)
        campaigns.append(campaign)

    campaign = campaigns[0]
    print >> sys.stderr, "3"
    #get campaign's users
    users = []
    cur = db.cursor()
    command = "select * from ssim_annotation.user where user.iduser in (select iduser from campaign_users where idCampaign =" + str(campaign.id) +");"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

        user = User(unicode(idUser),fullname, email, password_codified, role, active,0)
        users.append(user)
    print >> sys.stderr, "4"
    #get campaign's one-shot users
    one_shot_users = []
    cur = db.cursor()
    command = "select * from ssim_annotation.one_shot_user where idRun =" + str(run.id) +";"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        occupied = row[1]
        idCampaign = row[2]
		
        user = OneShotUser(unicode(idUser),occupied, idCampaign,0)
        one_shot_users.append(user)
    #print >> sys.stderr, "2"
    #get campaign's script
    scripts = []
    cur = db.cursor()
    command = "SELECT * FROM ssim_annotation.script where idScript = " + str(campaign.idScript) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idScript = row[0]
        name = row[1]
        filepath = row[2]

        script = Script(idScript,name,filepath,"")
        scripts.append(script)

    script = scripts[0]
    print >> sys.stderr, "5"
    print run.startDate
    #get tweets from Solr
    endDate = datetime.datetime.strptime(run.startDate, '%Y-%m-%d')
    initDate = endDate - datetime.timedelta(days=campaign.deltaTime)
    #print >> sys.stderr, "a"
    init = str(initDate).replace(" ","T") + "Z"
    end = str(endDate).replace(" ","T") + "Z"
    #print >> sys.stderr, "b"
    #print >> sys.stderr, run.__dict__
    separatedQueries = run.solrQuery.split(";")
    query_string = []
    target = []
    for query in separatedQueries:
        query_string.append("text:" + query + " AND is_rt_b:False AND created_at:[" + '"' + init + '"' + " TO " + '"' + end + '"' + "]")
    #print >> sys.stderr, "c"
    dictionary = {}
    
    cur = db.cursor()
    command = "SELECT * FROM ssim_annotation.script where idScript = " + str(campaign.idScript) + ";"
    cur.execute(command)
    
    for x in xrange(0,len(query_string)):
        counter = 0
        start = 0
        while counter < int(querySize):
            start = 0
            response = s.query(query_string[x] ,start , sort="created_at desc")
            for hit in response.results:
                if counter >= int(querySize):
                    break
                idTweet = hit['id']
                text = hit['text'].replace("\n","")
                cur = db.cursor()
                command = "INSERT INTO `tweets`(`id_tweet`, `id_campaign`, `target`) VALUES ("+str(idTweet)+","+str(idCampaign)+",'"+solrTarget[x]+"');"
                cur.execute(command)
                cur = db.cursor()
                command = "SELECT LAST_INSERT_ID();"
                cur.execute(command)
                for row in cur.fetchall():
                    id = row[0]
                dictionary[id] = text
                counter+=1
            start+=10

        counter = 0

    #randomize results and filter number of tweets retrieved

    tweets = dictionary.keys()
    shuffle(tweets)
    tweets = tweets[0:campaign.numberAnnotations]

    print >> sys.stderr, "6"
    #print >> sys.stderr, dictionary.keys()

    #save candidate tweets
    
    keys = dictionary.keys()
    random.shuffle(keys)
    #print >> sys.stderr, keys
    for key in keys:
        #print >> sys.stderr, key
        tweet_id = key

        command = "SELECT count(*) FROM ssim_annotation.candidate_for_selection where idTweet = " + str(tweet_id) + " and idRun = " + str(run.id) + ";"
        cur.execute(command)
        for row in cur.fetchall():
            count1 = row[0]
        #print >> sys.stderr, "antes adicionar"
        if count1 == 0:        #item not in database yet
            command = "insert into ssim_annotation.candidate_for_selection (idRun,idTweet,selectedForAttribution) values (" + str(run.id) + "," + str(tweet_id) + ",0);"
            cur.execute(command)        
        #print >> sys.stderr, "depois adicionar"
    db.commit()
    print >> sys.stderr, "5"
    #TODO: call active learner to filter candidates, differentiate script call (R or python)
    #it includes re-organizing table candidate_for_selection

    #f.write(ppath + " -> " + script.filepath + "\n")
    #proc = subprocess.Popen("%s %s %s" % (ppath, script.filepath, data_path), stdout=subprocess.PIPE)


    #read table candidate_for_selection, extract selected tweets and clean candidate tweets for this run
    command = "SELECT * FROM ssim_annotation.candidate_for_selection where idRun = " + str(run.id) + ";"
    cur.execute(command)
    selectedTweets = []
    for row in cur.fetchall():
        idTweet = row[1]
        selected = row[2]
        if selected == 0:        #TODO: change to if selected == 1:
            selectedTweets.append(idTweet)

    print >> sys.stderr, "selected tweets"

    command = "DELETE FROM ssim_annotation.candidate_for_selection where selectedForAttribution=0 and idRun= " + str(run.id) + ";"
    cur.execute(command)
    db.commit()

    random.shuffle(selectedTweets)
    print >> sys.stderr, "6"
    #define control group and save annotations: select 10%
    if(len(selectedTweets) < 10):
        threshold = len(selectedTweets)
    elif(int(math.floor(0.05*len(selectedTweets))) > 10):
        threshold = int(math.floor(0.05*len(selectedTweets))) #int(math.floor(0.1*len(selectedTweets)))
    else:
	    threshold = 10
    counter = 0
    while counter < threshold:
        print >> sys.stderr, "a"
        rdm = int(random.random()*len(selectedTweets))
        print >> sys.stderr, "b"
        tweet = selectedTweets[rdm]
        selectedTweets.remove(tweet)
        print >> sys.stderr, "c"
        #assign control tweet to all normal users
        for user in users:
            print >> sys.stderr, "d"
            command = "SELECT count(*) FROM ssim_annotation.annotation where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            print >> sys.stderr, "e"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]
            print >> sys.stderr, "f"
            if count1 == 0:        #item not in database yet
                #count number of attributions
                command = "SELECT count(*) FROM ssim_annotation.annotation where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]
                print >> sys.stderr, "g"
                if attributions < campaign.numberAnnotations:    #verify if it does not exceed threshold
                    command = "insert into ssim_annotation.annotation (idUser,idTweet,idRun,agreement) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ",1);"
                    cur.execute(command)
        db.commit()
        print >> sys.stderr, "f"
        #assign tweet to all one-shot users
        for user in one_shot_users:
            command = "SELECT count(*) FROM ssim_annotation.annotation_one_shot where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]

            if count1 == 0:        #item not in database yet
                command = "SELECT count(*) FROM ssim_annotation.annotation_one_shot where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]

                if attributions < campaign.numberAnnotations:    #verify if it does not exceed threshold
                    command = "insert into ssim_annotation.annotation_one_shot (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)
        db.commit()

        counter = counter + 1
    print >> sys.stderr, "7"
    #make attributions from remaining tweets and save annotations (if threshold has not been surpassed so far)
    for tweet in selectedTweets:
        length_users = len(users) + len(one_shot_users)
        rdm = int(random.random()*length_users)
        tmp = len(users) - 1
        if rdm > tmp:    #select one_shot_user and reserve special annotation
            new_rdm = rdm - len(users)
            user = one_shot_users[new_rdm]

            command = "SELECT count(*) FROM ssim_annotation.annotation_one_shot where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]

            if count1 == 0:        #item not in database yet
                command = "SELECT count(*) FROM ssim_annotation.annotation_one_shot where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]

                if attributions < campaign.numberAnnotations:    #verify if it does not exceed threshold
                    command = "insert into ssim_annotation.annotation_one_shot (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)

        else:
            user = users[rdm]

            command = "SELECT count(*) FROM ssim_annotation.annotation where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]

            if count1 == 0:        #item not in database yet
                command = "SELECT count(*) FROM ssim_annotation.annotation where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]

                if attributions < campaign.numberAnnotations:    #verify if it does not exceed threshold
                    command = "insert into ssim_annotation.annotation (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)
    
    db.commit()
    print >> sys.stderr, "8"

    """for tweet in tweets:
        for user in users:
            print >> sys.stderr, "User ID :"
            print >> sys.stderr, str(user.id)
            print >> sys.stderr, "Tweet ID :"
            print >> sys.stderr, str(tweet)
            print >> sys.stderr, "Run ID :"
            print >> sys.stderr, str(run.id)
            print >> sys.stderr, "\n"
            command = "insert into ssim_annotation.annotation(idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
            cur.execute(command)"""


    #update run status
    cur = db.cursor()
    command = "UPDATE ssim_annotation.run SET status = " + '"' + "active" + '"' + " where idRun = " + str(run.id) + ";"
    cur.execute(command)
    cur.connection.commit();
    print >> sys.stderr, "9"

    #send email
    sendEmail("Your account was selected to start a new annotation run.\nPlease visit 192.168.102.190:3333 and login with your credentials.", "New annotation run", users)

@app.route("/StopCampaign/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def stopCampaign(id):

    #get schedulled runs and set as closed
    runs = []
    cur = db.cursor()
    command = "SELECT * FROM run where idCampaign = " + str(id) + " and status = " + '"' + "schedulled" + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idRun = row[0]
        startDate = str(row[1]).split(" ")[0]
        endDate = str(row[2]).split(" ")[0]

        run = Run(idRun,startDate,endDate,"",0,0,0)

        cur = db.cursor()
        command = "UPDATE run SET status = " + '"' + "closed" + '"' + " where idRun = " + str(run.id) + ";"
        cur.execute(command)
        db.commit();

    return redirect(url_for('viewCampaign', id=id))

#@app.route("/DeleteCampaign/<string:id>", methods = ['GET'])
#@login_required
#@requires_roles('admin')
def deleteCampaign(id):
    campaign = Campaign(0, "", "", "", "", "", "","",0,0,0)
    cur = db.cursor()
    command = "SELECT * FROM campaign where idCampaign = " + str(id) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]
        deltaTime = row[5]
        idScript = row[6]

        campaign = Campaign(idCampaign, name, startDate, endDate, period, deltaTime, idScript,"",0,0,0)

    if campaign.id != 0:    #campaign exists
        cur1 = db.cursor()
        command = "SELECT * FROM run where idCampaign = " + str(id) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            idRun = row[0]
            startDate = str(row[1]).split(" ")[0]
            endDate = str(row[2]).split(" ")[0]

            run = Run(idRun,startDate,endDate,"",0,0,0)

            print >> sys.stderr, ("deleting run: " + str(run.id))

            cur3 = db.cursor()
            command = "DELETE FROM run where idRun = " + str(idRun) + ";"
            cur3.execute(command)

            cur2 = db.cursor()
            command = "SELECT * FROM annotation where idRun = " + str(run.id) + ";"
            cur2.execute(command)
            for row in cur2.fetchall():
                idUser = row[0]
                idTweet = row[1]
                idRun = row[2]
                annotationDate = str(row[3]).split(" ")[0]
                isClosed = row[4]
                polarity = row[5]
                annotation = Annotation("", idUser, idTweet, idRun, annotationDate, "", isClosed, "", idCampaign,name)

                print >> sys.stderr, ("deleting annotation: " + str(annotation.idRun) + " -> " +  str(annotation.idUser) + " -> " + str(annotation.idTweet))

                cur3 = db.cursor()
                command = "DELETE FROM annotation where idRun = " + str(idRun) + ";"
                cur3.execute(command)

        db.commit();
        cur3 = db.cursor()
        command = "SELECT * FROM campaign_users where idCampaign = " + str(campaign.id) + ";"
        cur2.execute(command)
        for row in cur2.fetchall():
            idUser = row[0]
            idCampaign = row[1]

            print >> sys.stderr, str("deleting user in campaign: " + str(idUser) + " -> " +  str(idCampaign))

            cur3 = db.cursor()
            command = "DELETE FROM campaign_users where idCampaign = " + str(campaign.id) + ";"
            cur3.execute(command)
        db.commit();
    #annotation, run, campaign_users, campaign

    print >> sys.stderr, ("deleting Campaign: " + str(campaign.id))

    cur3 = db.cursor()
    command = "DELETE FROM campaign where idCampaign = " + str(campaign.id) + ";"
    cur3.execute(command)
    db.commit();
    return redirect(url_for('profile'))

@app.route("/ListCampaigns", methods = ['GET'])
@login_required
@requires_roles('admin')
def listCampaigns():
    campaigns = []
    cur = db.cursor()
    command = "SELECT * FROM campaign;"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]
        deltaTime = row[5]
        idScript = row[6]

        closed=0
        cur1 = db.cursor()
        command = "select count(*) from annotation where annotation.isClosed = 1 and annotation.idRun in ( select idRun from run where idCampaign=" + str(idCampaign) + ");"
        cur1.execute(command)
        for row in cur1.fetchall():
            closed=row[0]

        total=0
        cur1 = db.cursor()
        command = "select count(*) from annotation where annotation.idRun in ( select idRun from run where idCampaign=" + str(idCampaign) + ");"
        cur1.execute(command)
        for row in cur1.fetchall():
            total=row[0]

        if total != 0:    #campaigns that have already started
            ratio = round(float(closed)/float(total) * 100)
            campaign = Campaign(idCampaign, name, startDate, endDate, period, deltaTime, idScript,"",closed,total,ratio)
            campaigns.append(campaign)

    return render_template('listCampaigns.html', campaigns=campaigns)

@app.route("/ViewCampaign/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def viewCampaign(id):
    cur = db.cursor()
    command = "SELECT * FROM campaign where idCampaign = " + id + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]

        periodDays = 0
        if period == 1:
            periodDays= "1 Week";
        elif period == 7:
            periodDays = "1 Week"
        else:
            periodDays = "1 Month"
        deltaTime = row[5]
        idScript = row[6]
        campaign = Campaign(idCampaign, name, startDate, endDate, periodDays, deltaTime, idScript,"",0,0,0)

    #get script by id
    cur = db.cursor()
    command = "SELECT * FROM script where idScript = " + str(campaign.idScript) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idScript = row[0]
        name = row[1]
        filepath = row[2]

        script = Script(idScript,name,filepath,filepath)

    #get runs
    runs = []
    cur = db.cursor()
    command = "SELECT * FROM run where idCampaign = " + str(campaign.id) + " and status = " + '"' + "active" + '"' + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idRun = row[0]
        startDate = str(row[1]).split(" ")[0]
        endDate = str(row[2]).split(" ")[0]

        run = Run(idRun,startDate,endDate,"",0,0,0)
        runs.append(run)

    #get users
    users = []
    cur = db.cursor()
    command = "select * from user where user.iduser in (select iduser from campaign_users where idCampaign =" + str(campaign.id) +");"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

        value_counter=0
        for run in runs:
            cur1 = db.cursor()
            command = "SELECT count(*) FROM annotation where idClassification_label != 1 and idUser=" + str(idUser) + " and idRun = " +str(run.id) + ";"
            cur1.execute(command)
            value1 = 0
            for row in cur1.fetchall():
                value1 = row[0]

            #print value1
            value_counter = value_counter + value1

        value_counter1=0
        for run in runs:
            cur1 = db.cursor()
            command = "SELECT count(*) FROM annotation where idUser=" + str(idUser) + " and idRun = " +str(run.id) + ";"
            cur1.execute(command)
            value1 = 0
            for row in cur1.fetchall():
                value1 = row[0]

            value_counter1 = value_counter1 + value1

        ratio = float("{0:.2f}".format(float(value_counter)/float(value_counter1) *100))
        user = User(unicode(idUser),fullname, email, password_codified, role, active,ratio)
        users.append(user)

    #get campaign status
    cur1 = db.cursor()
    command = "SELECT count(*) FROM run where idCampaign=" + str(campaign.id) + " and status = " + '"' + "closed" + '"' + ";"
    cur1.execute(command)
    value1 = 0
    for row in cur1.fetchall():
        value1 = row[0]

    status = "ok"
    if value1 > 0:
        status = "closed"
    return render_template('viewCampaign.html', campaign = campaign, script=script, users = users, runs=runs, status=status)

@app.route("/ViewCampaignUser/<string:id>", methods = ['GET'])
@login_required
def viewCampaignUser(id):
    cur = db.cursor()
    command = "SELECT * FROM campaign where idCampaign = " + id + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]

        periodDays = 0
        if period == 1:
            periodDays= "1 Week";
        elif period == 7:
            periodDays = "1 Week"
        else:
            periodDays = "1 Month"
        deltaTime = row[5]
        idScript = row[6]
        campaign = Campaign(idCampaign, name, startDate, endDate, periodDays, deltaTime, idScript,"",0,0,0)

    #get runs
    runs = []
    cur = db.cursor()
    command = "SELECT * FROM run where idCampaign = " + str(campaign.id) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idRun = row[0]
        startDate = str(row[1]).split(" ")[0]
        endDate = str(row[2]).split(" ")[0]

        closed=0
        cur1 = db.cursor()
        command = "select count(*) from annotation where annotation.isClosed = 1 and annotation.idUser =" + str(current_user.id) + " and annotation.idRun =" + str(idRun) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            closed=row[0]

        total=0
        cur1 = db.cursor()
        command = "select count(*) from annotation where annotation.idUser =" + str(current_user.id) + " and annotation.idRun =" + str(idRun) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            total=row[0]

        if total != 0:    #campaigns that have already started
            ratio = round(float(closed)/float(total) * 100)
            run = Run(idRun,startDate,endDate,"",closed,total,ratio)
            runs.append(run)


    return render_template('viewCampaignUser.html', campaign = campaign, runs=runs)

def queryPolarity(polarity,idRun):
    cur = db.cursor()
    cur.execute("SELECT count(*) FROM annotation where idRun = " + str(idRun) + " and idClassification_label = " + str(polarity) + ";")
    for row in cur.fetchall():
        count = row[0]

    cur.execute("SELECT count(*) FROM annotation_one_shot where idRun = " + str(idRun) + " and idClassification_label = " + str(polarity) + ";")
    for row in cur.fetchall():
        count1 = row[0]

    result = count + count1
    return result

@app.route("/StatisticsCampaign/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def statisticsCampaign(id,chartID = 'chart_ID', chart_type = 'line', chart_height = 450):
    chart = {"renderTo": chartID, "type": chart_type, "height": chart_height}

    cur = db.cursor()
    command = "SELECT * FROM campaign where idCampaign = " + id + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idCampaign = row[0]
        name = row[1]
        startDate = str(row[2]).split(" ")[0]
        endDate = str(row[3]).split(" ")[0]
        period = row[4]

        periodDays = 0
        if period == 1:
            periodDays= "1 Week";
        elif period == 7:
            periodDays = "1 Week"
        else:
            periodDays = "1 Month"
        deltaTime = row[5]
        idScript = row[6]
        campaign = Campaign(idCampaign, name, startDate, endDate, periodDays, deltaTime, idScript,"",0,0,0)

    #get runs
    value1 = 0
    value2 = 0
    value3 = 0
    value4 = 0
    value5 = 0
    value6 = 0
    total_counter = 0

    cur = db.cursor()
    command = "SELECT * FROM run where idCampaign = " + str(campaign.id) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idRun = row[0]

        cur.execute("SELECT count(*) FROM annotation where idRun = " + str(idRun) + ";")
        for row in cur.fetchall():
            count1 = row[0]

        cur.execute("SELECT count(*) FROM annotation_one_shot where idRun = " + str(idRun) + ";")
        for row in cur.fetchall():
            count2 = row[0]

        if count1 != 0:    #run hasn't started yet
            total_counter = total_counter + count1 + count2
            #TODO: change to polarities associated in external table (different ids)
            """
            cur1 = db.cursor()
            command = "SELECT * FROM campaign_classification_labels where idCampaign = " + str(campaign.id) + ";"
            cur1.execute(command)
            for row in cur1.fetchall():
                count1 = row[0]
            """

            value6 = value6 + queryPolarity(1,idRun)    #missing
            value1 = value1 + queryPolarity(2,idRun)    #negative
            value2 = value2 + queryPolarity(3,idRun)    #positive
            value3 = value2 + queryPolarity(4,idRun)    #neutral
            value4 = value4 + queryPolarity(5,idRun)    #objective
            value5 = value5 + queryPolarity(6,idRun)    #not clear


    value1 = float("{0:.2f}".format(float(value1)/float(total_counter) *100))
    value2 = float("{0:.2f}".format(float(value2)/float(total_counter) *100))
    value3 = float("{0:.2f}".format(float(value3)/float(total_counter) *100))
    value4 = float("{0:.2f}".format(float(value4)/float(total_counter) *100))
    value5 = float("{0:.2f}".format(float(value5)/float(total_counter) *100))
    value6 = float("{0:.2f}".format(float(value6)/float(total_counter) *100))

    #chart
    chartID = 'chart_ID3'
    chart_type = 'pie'
    chart = {"renderTo": chartID, "type": chart_type, "height": chart_height}

    xAxis = {"categories": []}
    yAxis = {"title": {"text": 'Average polarity'}}

    series = [{"name": 'percentage', "data": [["negative",value1],["positive",value2],["neutral",value3],["objective",value4],["not clear",value5],["missing",value6]]}]
    title = {"text": 'Polarity Percentages'}

    return render_template('statisticsCampaign.html', chartID=chartID, chart=chart, series=series, title=title,xAxis=xAxis, yAxis=yAxis,)

@app.route("/CalculateAgreement/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def agreementCampaign(id):
	
    campaignTweets = []
    campaignTweetsText = []
    runs = []
    sums = []
    agreement = []
    toy_data = []

    cur = db.cursor()
    command = "SELECT id,id_tweet FROM tweets where id_campaign=" + str(id) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        campaignTweets.append(row[0])
        text=""
        query_string = "id:" + str(row[1])
        response = s.query(query_string)
        for hit in response.results:
            text = hit['text'].replace("\n","")
        campaignTweetsText.append(text)
    cur = db.cursor()
    command = "SELECT idRun FROM run where idCampaign=" + str(id) + ";"
    cur.execute(command)
    for row in cur.fetchall():
	    runs.append(row[0])
    
    for tweet in campaignTweets:
        for run in runs:
            cur = db.cursor()
            command = "SELECT idUser,idClassification_label FROM annotation where idRun=" + str(run) + " AND idTweet=" + str(tweet) + " AND idClassification_label <> 1 AND agreement=1;"
            cur.execute(command)
            for row in cur.fetchall():
                print >> sys.stderr,row
                toy_data.append([str(row[0]),int(tweet),str(row[1])])
        task = nltk.metrics.agreement.AnnotationTask(data=toy_data)
        sums.append(task.alpha())
        
        
    print >> sys.stderr,sums
    for x in xrange(0,len(sums)):
        agreement.append(Agreement(campaignTweetsText[x],sums[x]*100))
    return render_template('agreementCampaign.html', agreement=agreement,)

@app.route("/ExtractCampaign/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def extractCampaign(id):

    extractFile = codecs.open("results/Campaign:" + id +".csv", 'w',"utf-8-sig")

    extractFile.truncate()
    
    extractFile.write("idTweet;tweet;target;label;idUser \n")
    
    cur = db.cursor()
    command = "SELECT idRun FROM run where idCampaign=" + str(id) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        cur1 = db.cursor()
        command1 = "SELECT idTweet,idUser, idClassification_label FROM annotation where idRun=" + str(row[0]) + " and idClassification_label <> 1;"
        cur1.execute(command1)
        for row1 in cur1.fetchall():
            idTweet = row1[0]
            idUser = row1[1]
            idClassLabel = row1[2]
            Label = ""
            cur2 = db.cursor()
            command2 = "SELECT name FROM classification_label where idClassification_label=" + str(idClassLabel) + ";"
            cur2.execute(command2)
            for row2 in cur2.fetchall():
				Label = row2[0]
            cur3 = db.cursor()
            command3 = "SELECT id_tweet,target FROM tweets where id=" + str(idTweet) + ";"
            cur3.execute(command3)
            idTweets = ""
            target = ""
            for row3 in cur3.fetchall():
				idTweets = row3[0]
				target = row3[1]
            text=""
            query_string = "id:" + str(idTweets)
            response = s.query(query_string)
            for hit in response.results:
                text = hit['text'].replace("\n","")
            extractFile.write(str(idTweet)+";"+text+";"+target+";"+Label+";"+str(idUser)+"\n")
			    
        
    
    extractFile.close()

    return redirect(url_for('profile'))


@app.route("/ViewRun/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def viewRun(id):
    #get normal annotations
    annotations = []
    cur = db.cursor()
    command = "SELECT * FROM annotation where idRun=" + str(id) + ";"
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        idUser = row[0]
        idTweet = row[1]
        idRun = row[2]
        annotationDate = str(row[3]).split(" ")[0]
        isClosed = row[4]
        polarity = row[5]

        #get polarity label name
        cur1 = db.cursor()
        command = "SELECT name FROM classification_label where idClassification_label=" + str(polarity) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            polarityName = row[0]
        #print polarityName
        #get user name
        cur1 = db.cursor()
        command = "SELECT fullname FROM user where idUser=" + str(idUser) + ";"
        cur1.execute(command)

        name = ""
        for row in cur1.fetchall():
            name = row[0].decode('iso-8859-1')

        #get tweet text
        text=""
        query_string = "id:" + str(idTweet)
        response = s.query(query_string)
        for hit in response.results:
            idtweet = hit['id']
            text = hit['text'].replace("\n","")

        if text != "":
            #get campaign id
            command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                idCampaign = row[0]

            annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarityName, isClosed, text, idCampaign,name)
            annotations.append(annotation)

            result = result + 1

    #get one shot annotations
    one_shot_annotations = []
    cur = db.cursor()
    command = "SELECT * FROM annotation_one_shot where idRun=" + str(id) + ";"
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        idUser = row[0]
        idTweet = row[1]
        idRun = row[2]
        annotationDate = str(row[3]).split(" ")[0]
        isClosed = row[4]
        polarity = row[5]

        #get polarity label name
        cur1 = db.cursor()
        command = "SELECT name FROM classification_label where idClassification_label=" + str(polarity) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            polarityName = row[0]

        name = ""

        #get tweet text
        text=""
        query_string = "id:" + str(idTweet)
        response = s.query(query_string)
        for hit in response.results:
            idtweet = hit['id']
            text = hit['text'].replace("\n","")

        if text != "":
            #get campaign id
            command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                idCampaign = row[0]

            annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarityName, isClosed, text, idCampaign,name)
            one_shot_annotations.append(annotation)

            result = result + 1


    #get one_shot_users
    one_shot_users = []
    cur1 = db.cursor()
    command = "select * from one_shot_user where idRun =" + str(id) +";"
    cur1.execute(command)
    for row in cur1.fetchall():
        idUser = row[0]
        occupied = row[1]

        cur1 = db.cursor()
        command = "SELECT count(*) FROM annotation_one_shot where idClassification_label != 1 and idUser=" + str(idUser) + " and idRun = " +str(id) + ";"
        value_counter=0
        cur1.execute(command)
        value1 = 0
        for row in cur1.fetchall():
            value1 = row[0]

        value_counter = value1

        value_counter1=0
        cur1 = db.cursor()
        command = "SELECT count(*) FROM annotation_one_shot where idUser=" + str(idUser) + " and idRun = " +str(id) + ";"
        cur1.execute(command)
        value1 = 0
        for row in cur1.fetchall():
            value1 = row[0]

        value_counter1 = value1

        ratio = float("{0:.2f}".format(float(value_counter)/float(value_counter1) *100))
        #print ratio

        user_one_shot = OneShotUser(unicode(idUser),occupied, id, ratio)
        one_shot_users.append(user_one_shot)

    #get users
    users = []
    cur = db.cursor()
    command = "select * from user where user.iduser in (select iduser from campaign_users where idCampaign in (select idCampaign from run where idRun=" + str(id) +"));"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        fullname = row[1].decode('iso-8859-1')
        email = row[2]
        password_codified = row[3]
        active = row[4]
        isAdmin = row[5]

        role = "regular"
        if isAdmin == 1:
            role="admin"

        value_counter=0
        cur1 = db.cursor()
        command = "SELECT count(*) FROM annotation where idClassification_label != 1 and idUser=" + str(idUser) + " and idRun = " +str(id) + ";"
        #print command
        cur1.execute(command)
        value1 = 0
        for row in cur1.fetchall():
            value1 = row[0]

        value_counter = value1
        #print value_counter

        value_counter1=0
        cur1 = db.cursor()
        command = "SELECT count(*) FROM annotation where idUser=" + str(idUser) + " and idRun = " +str(id) + ";"
        #print command
        cur1.execute(command)
        value1 = 0
        for row in cur1.fetchall():
            value1 = row[0]

        #print value1
        value_counter1 = value_counter1 + value1
        #print value_counter1

        ratio = float("{0:.2f}".format(float(value_counter)/float(value_counter1) *100))
        #print ratio
        user = User(unicode(idUser),fullname, email, password_codified, role, active,ratio)
        users.append(user)

    return render_template('viewRun.html', annotations=annotations, one_shot_annotations=one_shot_annotations, one_shot_users=one_shot_users, users=users)

@app.route("/ViewRunOneShot/<string:id>", methods = ['GET'])
@login_required
@requires_roles('admin')
def viewRunOneShot(id):
    #print "here"
    targets = []
    annotations = []
    cur = db.cursor()
    command = "SELECT * FROM annotation_one_shot where idRun=" + str(id) + ";"
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        idUser = row[0]
        idTweet = row[1]
        idRun = row[2]
        annotationDate = str(row[3]).split(" ")[0]
        isClosed = row[4]
        polarity = row[5]

        #get polarity label name
        cur1 = db.cursor()
        command = "SELECT name FROM classification_label where idClassification_label=" + str(polarity) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            polarityName = row[0]
        #print polarityName
        #get user name
        name = ""

        cur1 = db.cursor()
        command = "SELECT id_tweet,target FROM tweets where id=" + str(idTweet) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            TweetID = row[0]
            target = row[1]

        #get tweet text
        text=""
        query_string = "id:" + str(TweetID)
        response = s.query(query_string)
        for hit in response.results:
            id = hit['id']
            text = hit['text'].replace("\n","")
            print >> sys.stderr,hit

        if text != "":
            #get campaign id
            command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                idCampaign = row[0]

            annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarityName, isClosed, text, idCampaign,name,target)
            annotations.append(annotation)

            result = result + 1

    return render_template('viewRunOneShot.html', annotations=annotations)

@app.route("/AnnotationsRun/<string:id>", methods = ['GET'])
def annotationsRun(id):
    annotations = []
    cur = db.cursor()
    command = "SELECT * FROM annotation where idRun=" + str(id) + ";"
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        idUser = row[0]
        idTweet = row[1]
        idRun = row[2]
        annotationDate = str(row[3]).split(" ")[0]
        isClosed = row[4]
        polarity = row[5]

        #get polarity label name
        cur1 = db.cursor()
        command = "SELECT name FROM classification_label where idClassification_label=" + str(polarity) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            polarityName = row[0]
        #print polarityName
        #get user name
        cur1 = db.cursor()
        command = "SELECT fullname FROM user where idUser=" + str(idUser) + ";"
        cur1.execute(command)

        name = ""
        for row in cur1.fetchall():
            name = row[0].decode('iso-8859-1')

        #get tweet text
        text=""
        """
        query_string = "id:" + str(idTweet)
        response = s.query(query_string)
        for hit in response.results:
            id = hit['id']
            text = hit['text'].replace("\n","")

        if text != "":
        """
        #get campaign id
        command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
        cur.execute(command)
        for row in cur.fetchall():
            idCampaign = row[0]

        annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarityName, isClosed, text, idCampaign,name)
        annotations.append(annotation.to_JSON())

        result = result + 1
    return json.dumps(annotations)

@app.route("/AnnotationsRunOneShot/<string:id>", methods = ['GET'])
def annotationsRunOneShot(id):
    annotations = []
    cur = db.cursor()
    command = "SELECT * FROM annotation_one_shot where idRun=" + str(id) + ";"
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        idUser = row[0]
        idTweet = row[1]
        idRun = row[2]
        annotationDate = str(row[3]).split(" ")[0]
        isClosed = row[4]
        polarity = row[5]

        #get polarity label name
        cur1 = db.cursor()
        command = "SELECT name FROM classification_label where idClassification_label=" + str(polarity) + ";"
        cur1.execute(command)
        for row in cur1.fetchall():
            polarityName = row[0]
        #print polarityName
        #get user name
        name = ""

        #get tweet text
        text=""
        """
        query_string = "id:" + str(idTweet)
        response = s.query(query_string)
        for hit in response.results:
            id = hit['id']
            text = hit['text'].replace("\n","")

        if text != "":
        """
        #get campaign id
        command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
        cur.execute(command)
        for row in cur.fetchall():
            idCampaign = row[0]

        annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarityName, isClosed, text, idCampaign,name)
        annotations.append(annotation.to_JSON())

        result = result + 1
    return json.dumps(annotations)

@app.route("/ViewRunUser/<string:id>&modal=<string:modal>", methods = ['GET'])
@login_required
def viewRunUser(id,modal):
    annotations = []
    labels = []
    cur = db.cursor()
    targets = []
    command = "SELECT * FROM annotation where idRun=" + str(id) + " and idUser = " + str(current_user.id) + " and isClosed=0;"
    #print command
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        if result <5:
            idUser = row[0]
            idTweet = row[1]
            idRun = row[2]
            annotationDate = str(row[3]).split(" ")[0]
            polarity = row[4]
            isClosed = row[5]
            

            #get user name
            cur1 = db.cursor()
            command = "SELECT fullname FROM user where idUser=" + str(idUser) + ";"
            cur1.execute(command)

            name = ""
            for row in cur1.fetchall():
                name = row[0].decode('iso-8859-1')

            #get campaign's labels
            labels = []
            labelDescriptor = ""
            cur1 = db.cursor()
            command = "select * from classification_label where idClassification_label in (select idClassification_label from campaign_classification_labels where idCampaign in ( SELECT idCampaign FROM campaign where idCampaign in ( select idCampaign from run where idRun=" + str(idRun) + ")));"
            cur1.execute(command)
            for row in cur1.fetchall():
                idLabel = row[0]
                nameLabel = row[1]
                descriptionLabel = row[2]
                if descriptionLabel != "":
                    labelDescriptor = labelDescriptor + "<p><b>" + str(nameLabel.upper()) + "</b>: " + str(descriptionLabel) + "</p>"
                label = ClassificationLabel(idLabel,nameLabel,descriptionLabel);
                labels.append(label)

            #name = ""
            #for row in cur1.fetchall():
            #    name = row[0].decode('iso-8859-1')

            cur1 = db.cursor()
            command = "SELECT id_tweet,target FROM tweets where id=" + str(idTweet) + ";"
            cur1.execute(command)
            for row in cur1.fetchall():
                TweetID = row[0]
                target = row[1]

            #get tweet text
            text=""
            query_string = "id:" + str(TweetID)
            response = s.query(query_string)
            for hit in response.results:
                id = hit['id']
                text = hit['text'].replace("\n","")
                print >> sys.stderr,hit
                

            if text != "":
                #get campaign id
                command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    idCampaign = row[0]

                annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarity, isClosed, text, idCampaign,name,target)
                annotations.append(annotation)

                result = result + 1
                
    
    if annotations == []:
        flash("You have successfully annotated all tweets for this run.","success")
        return redirect(url_for('profile'))

    return render_template('viewRunUser.html', annotations=annotations, labels=labels, labelDescriptor=labelDescriptor, modal=modal)

@app.route("/addAnnotation", methods = ['POST'])
@login_required
def addAnnotation():
    #print request.form

    hypothesis = ['polarityRow1','polarityRow2','polarityRow3','polarityRow4','polarityRow5']
    counter=1
    for item in hypothesis:
        annotations = request.form.getlist(item)
        #print annotations
        if annotations != []:
            counter = counter + 1
        else:
            break;

    counter = counter - 1
    #print counter
    run = request.form.getlist("run1")[0]
    numberRows=request.form['rows']

    if str(numberRows)!=str(counter):
        flash("You must annotate every tweet listed before submitting.","error")
        return redirect(url_for('viewRunUser', id = run, modal="false"))

    idRun = -1
    counter1 = 0
    while counter1 < counter:
        tmp = counter1 + 1
        tweet = request.form.getlist("tweet"+str(tmp))[0]
        user = request.form.getlist("user"+str(tmp))[0]
        run = request.form.getlist("run"+str(tmp))[0]
        polarity = request.form.getlist("polarityRow"+str(tmp))[0]
        idRun = run

        """
        print tweet
        print user
        print run
        print polarity
        """

        todayDate = str(datetime.datetime.now()).split(" ")[0]  #'%Y-%m-%d'

        #update annotation in database
        cur = db.cursor()
        command = "UPDATE annotation SET idClassification_label = " + polarity + ",annotationDate = " + '"' + todayDate + '"' + ", isClosed = 1 where idUser = " + str(user) + " and idRun = " + str(run) + " and idTweet = " + str(tweet) + ";"
        #print command
        cur.execute(command)
        db.commit();

        counter1 = counter1 + 1

    return redirect(url_for('viewRunUser', id = idRun, modal="false"))

@app.route("/OneShotUserAssignment", methods = ['GET'])
def oneShotUserAssign():
    #get user
    cur = db.cursor()
    command = "SELECT * FROM one_shot_user where isOccupied=0;"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        occupied = row[1]
        idCampaign = row[2]
        print row

        #verify if there are annotations schedulled for this user
        run = 0
        cur = db.cursor()
        command = "SELECT * FROM annotation_one_shot where idUser = " + str(idUser) + ";"
        print idUser;
        cur.execute(command)
        for row in cur.fetchall():
            print row
            run = row[2]

        if run != 0:
            #assign user
            command = "UPDATE one_shot_user SET isOccupied=1 WHERE idUser = " + str(idUser) + ";"
            cur.execute(command)
            db.commit()

            user = OneShotUser(unicode(idUser), occupied, idCampaign, 0)
            return redirect(url_for('oneShotAnnotation', idUser=str(idUser), modal="true"))
            break
    flash("Unfortunatelly, there are no available annotations schedulled. Please try again later.","success")
    return redirect(url_for('hello'))

@app.route("/addAnnotationOneShot/<string:idUser>&modal=<string:modal>", methods = ['GET'])
def oneShotAnnotation(idUser,modal):
    annotations = []
    labels = []
    cur = db.cursor()

    #get assigned run
    run = 0
    cur = db.cursor()
    command = "SELECT * FROM annotation_one_shot where idUser = " + str(idUser) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        run = row[2]

    command = "SELECT * FROM annotation_one_shot where idRun=" + str(run) + " and idUser = " + str(idUser) + " and isClosed=0;"
    #print command
    cur.execute(command)
    result = 0
    for row in cur.fetchall():
        if result <5:
            idUser = row[0]
            idTweet = row[1]
            idRun = row[2]
            annotationDate = str(row[3]).split(" ")[0]
            polarity = row[4]
            isClosed = row[5]

            name = ""
            labelDescriptor =""
            #get campaign's labels
            labels = []
            cur1 = db.cursor()
            command = "select * from classification_label where idClassification_label in (select idClassification_label from campaign_classification_labels where idCampaign in ( SELECT idCampaign FROM campaign where idCampaign in ( select idCampaign from run where idRun=" + str(idRun) + ")));"
            cur1.execute(command)
            for row in cur1.fetchall():
                idLabel = row[0]
                nameLabel = row[1]
                descriptionLabel = row[2]
                if descriptionLabel != "":
                    labelDescriptor = labelDescriptor + "<p><b>" + nameLabel.upper() + "</b>: " + descriptionLabel + "</p>"
                label = ClassificationLabel(idLabel,nameLabel,descriptionLabel);
                labels.append(label)

            name = ""
            for row in cur1.fetchall():
                name = row[0].decode('iso-8859-1')

            #get tweet text
            text=""
            query_string = "id:" + str(idTweet)
            response = s.query(query_string)
            for hit in response.results:
                id = hit['id']
                text = hit['text'].replace("\n","")

            if text != "":
                #get campaign id
                command = "SELECT idCampaign FROM run where idRun=" + str(idRun) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    idCampaign = row[0]

                annotation = Annotation(result, idUser, idTweet, idRun, annotationDate, polarity, isClosed, text, idCampaign,name)
                annotations.append(annotation)

                result = result + 1

    command = "SELECT count(*) FROM annotation_one_shot where idRun=" + str(run) + " and idUser = " + str(idUser) + " and isClosed=1;"
    cur.execute(command)
    complete = 0
    for row in cur.fetchall():
        complete = row[0]

    command = "SELECT count(*) FROM annotation_one_shot where idRun=" + str(run) + " and idUser = " + str(idUser) + ";"
    cur.execute(command)
    total = 0
    for row in cur.fetchall():
        total = row[0]

    if complete == total:
        flash("You have successfully annotated all tweets for this session. If you wish, you can retry.","success")
        return redirect(url_for('hello'))

    if annotations == []:
        flash("Unfortunatelly, there are no available annotations schedulled. Please try again later.","error")
        return redirect(url_for('hello'))

    return render_template('viewRunOneShotUser.html', annotations=annotations, labels=labels, labelDescriptor=labelDescriptor, modal=modal)

@app.route("/addAnnotationOneShot", methods = ['POST'])
def addAnnotationOneShot():
    #print request.form


    hypothesis = ['polarityRow1','polarityRow2','polarityRow3','polarityRow4','polarityRow5']
    counter=1
    for item in hypothesis:
        annotations = request.form.getlist(item)
        #print annotations
        if annotations != []:
            counter = counter + 1
        else:
            break;

    counter = counter - 1
    #print counter
    run = request.form.getlist("run1")[0]
    numberRows=request.form['rows']
    user = request.form.getlist("user1")[0]
    if str(numberRows)!=str(counter):
        flash("You must annotate every tweet listed before submitting.","error")
        return redirect(url_for('oneShotAnnotation', idUser = str(user), modal="false"))

    user = 0
    idRun = -1
    counter1 = 0
    while counter1 < counter:
        tmp = counter1 + 1
        tweet = request.form.getlist("tweet"+str(tmp))[0]
        user = request.form.getlist("user"+str(tmp))[0]
        run = request.form.getlist("run"+str(tmp))[0]
        polarity = request.form.getlist("polarityRow"+str(tmp))[0]
        idRun = run

        todayDate = str(datetime.datetime.now()).split(" ")[0]  #'%Y-%m-%d'

        #update annotation in database
        cur = db.cursor()
        command = "UPDATE annotation_one_shot SET idClassification_label = " + polarity + ",annotationDate = " + '"' + todayDate + '"' + ", isClosed = 1 where idUser = " + str(user) + " and idRun = " + str(run) + " and idTweet = " + str(tweet) + ";"
        #print command
        cur.execute(command)
        db.commit();

        counter1 = counter1 + 1

    return redirect(url_for('oneShotAnnotation', idUser = str(user), modal="false"))

@app.route("/reAssignOneShotUser/<string:id>/<string:idRun>", methods = ['GET'])
@login_required
@requires_roles('admin')
def reAssignOneShotUser(id,idRun):
    cur = db.cursor()
    command = "SELECT * FROM one_shot_user where idUser=" + id + ";"
    cur.execute(command)
    for row in cur.fetchall():
        occupied = row[1]

    if occupied == 1:
        new_status = "0"

        cur = db.cursor()
        command = "UPDATE one_shot_user SET isOccupied = " + new_status +" where idUser = " + id;
        cur.execute(command)
        db.commit()

    return redirect(url_for('viewRun', id=idRun))

#application = DebuggedApplication(app, True)
#app.run(debug = True)    

def calculateAgreement(idTweet, idRun):
    cur = db.cursor()
    command = "SELECT * FROM annotation WHERE idTweet = " + idTweet + " AND idRun = " + idRun + ";"
    cur.execute(command)
    
    toy_data = []
    
    for row in cur.fetchall():
        toy_data.append([str(row[0]),int(row[1]),str(row[5])])
        
    task = nltk.metrics.agreement.AnnotationTask(data=toy_data)

    return task.alpha()

MAIL_USERNAME = 'insertemail'
MAIL_PASSWORD =  'insertpass'
MAIL_SERVER = 'smtp.fe.up.pt'
MAIL_PORT = '587'
ADMINS = ['ei11078@fe.up.pt']

if not app.debug:
    import logging
    from logging import FileHandler
    file_handler = FileHandler("logfile"+str(datetime.datetime.now())+".log", "w")
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)


if __name__ == '__main__':
    #app.run(debug = True)
    app.run('0.0.0.0', port=3333, debug=False)
