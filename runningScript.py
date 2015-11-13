import MySQLdb
import solr
import unicodedata
import os
import datetime
import codecs
import subprocess
import random
import math
import smtplib
import sys
from random import shuffle
from email.mime.text import MIMEText

db = MySQLdb.connect(host="localhost",  # your host, usually localhost
                     user="root",  # your username
                     passwd="reaction",  # your password
                     db="tweets_annotation")  # name of the data base
db.autocommit(True)

SOLR_PATH = "/codebits/"  # "/portugal/tweets/"
SOLR_HOST = "pattie.fe.up.pt"  # "reaction.fe.up.pt"
SOLR_HTTP = "http://" + SOLR_HOST + SOLR_PATH
SOLR_USER = "popstar_pedrosaleiro"
SOLR_PASS = "p3dr0@2013!"
SOLR_QUERY_SIZE = 1000

emailText = "Greetings,\nA new annotation run has started and you have a new assignment, should you choose to accept it. Please visit the website for more details.\n\nBest regards,\nThe Tweet Sentiment Annotation System administration"
me = "tiagodscunha@gmail.com"

ppath = r'C:\Program Files\R\R-3.0.2\bin\Rscript.exe'
data_path = r'C:\Python27\annotationSystem\\'

s = solr.SolrConnection(SOLR_HTTP)  # , http_user = SOLR_USER, http_pass= SOLR_PASS)


class Run:
    def __init__(self, id, startDate, endDate, idCampaign, solrQuery):
        self.id = id
        self.startDate = startDate
        self.endDate = endDate
        self.idCampaign = idCampaign
        self.solrQuery = solrQuery


class Campaign:
    def __init__(self, id, name, startDate, endDate, period, deltaTime, idScript, numberAnnotations):
        self.name = name
        self.id = id
        self.startDate = startDate
        self.endDate = endDate
        self.period = period
        self.deltaTime = deltaTime
        self.idScript = idScript
        self.numberAnnotations = numberAnnotations


class User:
    def __init__(self, id, name, email, password, role, active):
        self.email = email
        self.password = password
        self.name = name
        self.id = id
        self.role = role
        self.active = active


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


class OneShotUser:
    def __init__(self, id, ocuppied, idCampaign):
        self.id = id
        self.occupied = occupied
        self.idCampaign = idCampaign


class Script:
    def __init__(self, id, name, filepath):
        self.name = name
        self.id = id
        self.filepath = filepath

def sendEmail(message, subject, users):
    print >> sys.stderr, "start sending email"
    for user in users:
        print >> sys.stderr, user.email
        fromaddr = 'socialbus@fe.up.pt'
        toaddrs  = user.email

        msg = "\r\n".join([
            "From: socialbus@fe.up.pt",
            "To: " + user.email,
            "Subject: " + subject,
            "",
            message
        ])

        print >> sys.stderr, "message built"

        # Credentials (if needed)
        username = 'socialbus'
        password = 'reactionpopstar14'

        # The actual mail send
        print >> sys.stderr, "start sending email"
        server = smtplib.SMTP('smtp.fe.up.pt')
        print >> sys.stderr, "start smtp server connection"
        server.starttls()
        print >> sys.stderr, "start tls"
        server.login(username,password)
        print >> sys.stderr, "login"
        server.sendmail(fromaddr, toaddrs, msg)
        print >> sys.stderr, "send email"
        server.quit()
        print >> sys.stderr, "email sent"

runs = []
today = datetime.datetime.now()
initDate = str(today).split(" ")[0]
print initDate
run = Run(0,"","",0,0)
cur = db.cursor()
command = "SELECT * FROM tweets_annotation.run where initDate= " + '"' + initDate + '"' + " and status=" + '"' + "schedulled" + '"' + ";"
cur.execute(command)
for row in cur.fetchall():
    print >> sys.stderr, "1"

    idRun = row[0]
    startDate = str(row[1]).split(" ")[0]
    endDate = str(row[2]).split(" ")[0]
    idCampaign = row[3]
    solrQuery = row[4]
    run = Run(idRun,startDate,endDate,idCampaign,solrQuery)
    print run
    print run.id
    print run.startDate
    print run.endDate

    print >> sys.stderr, "2"
    #get run's campaign
    campaign = Campaign(0,0,0,0,0,0,0,0)
    cur = db.cursor()
    command = "SELECT * FROM tweets_annotation.campaign where idCampaign = " + str(run.idCampaign) + ";"
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
        numberAnnotations = row[7]

        campaign = Campaign(idCampaign, name, startDate, endDate, periodDays, deltaTime, idScript,numberAnnotations)

    print >> sys.stderr, "3"
    #get campaign's users
    users = []
    cur = db.cursor()
    command = "select * from tweets_annotation.user where user.iduser in (select iduser from campaign_users where idCampaign =" + str(campaign.id) +");"
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

        user = User(unicode(idUser),fullname, email, password_codified, role, active)
        users.append(user)
    print >> sys.stderr, "4"
    #get campaign's one-shot users
    one_shot_users = []
    cur = db.cursor()
    command = "select * from tweets_annotation.one_shot_user where idRun =" + str(run.id) +";"
    cur.execute(command)
    for row in cur.fetchall():
        idUser = row[0]
        occupied = row[1]
        idCampaign = row[2]

        user = OneShotUser(unicode(idUser),occupied, idCampaign)
        one_shot_users.append(user)
    #print >> sys.stderr, "2"
    #get campaign's script
    script = Script(0,0,0)
    cur = db.cursor()
    command = "SELECT * FROM tweets_annotation.script where idScript = " + str(campaign.idScript) + ";"
    cur.execute(command)
    for row in cur.fetchall():
        idScript = row[0]
        name = row[1]
        filepath = row[2]

        script = Script(idScript,name,filepath)

    print >> sys.stderr, "5"
    #get tweets from Solr
    print run.startDate
    endDate = datetime.datetime.strptime(run.startDate, '%Y-%m-%d')
    initDate = endDate - datetime.timedelta(days=campaign.deltaTime)
    #print >> sys.stderr, "a"
    init = str(initDate).replace(" ","T") + "Z"
    end = str(endDate).replace(" ","T") + "Z"
    #print >> sys.stderr, "b"
    #print >> sys.stderr, run.__dict__
    query_string = run.solrQuery + " AND created_at:[" + '"' + init + '"' + " TO " + '"' + end + '"' + "]"
    print >> sys.stderr, query_string
    #print >> sys.stderr, "c"
    dictionary = {}
    counter = 0

    while counter < SOLR_QUERY_SIZE:
        response = s.query(query_string ,start=counter , sort="created_at desc")

        for hit in response.results:
            id = hit['id']
            text = hit['text'].replace("\n","")
            dictionary[id] = text

        counter = counter + 10

    #randomize results and filter number of tweets retrieved

    tweets = dictionary.keys()
    shuffle(tweets)
    tweets = tweets[0:campaign.numberAnnotations]
    print >> sys.stderr, tweets

    print >> sys.stderr, "6"

    print >> sys.stderr, "6"
    #print >> sys.stderr, dictionary.keys()

    #save candidate tweets
    """
    print >> sys.stderr, len(dictionary)
    keys = dictionary.keys()
    random.shuffle(keys)
    print >> sys.stderr, keys
    for key in keys:
        print >> sys.stderr, key
        tweet_id = key

        command = "SELECT count(*) FROM tweets_annotation.candidate_for_selection where idTweet = " + str(tweet_id) + " and idRun = " + str(run.id) + ";"
        cur.execute(command)
        for row in cur.fetchall():
            count1 = row[0]
        #print >> sys.stderr, "antes adicionar"
        if count1 == 0:		#item not in database yet
            command = "insert into tweets_annotation.candidate_for_selection (idRun,idTweet,selectedForAttribution) values (" + str(run.id) + "," + str(tweet_id) + ",0);"
            cur.execute(command)
        #print >> sys.stderr, "depois adicionar"
    db.commit()
    print >> sys.stderr, "5"
    #TODO: call active learner to filter candidates, differentiate script call (R or python)
    #it includes re-organizing table candidate_for_selection

    #f.write(ppath + " -> " + script.filepath + "\n")
    #proc = subprocess.Popen("%s %s %s" % (ppath, script.filepath, data_path), stdout=subprocess.PIPE)


    #read table candidate_for_selection, extract selected tweets and clean candidate tweets for this run
    command = "SELECT * FROM tweets_annotation.candidate_for_selection where idRun = " + str(run.id) + ";"
    cur.execute(command)
    selectedTweets = []
    for row in cur.fetchall():
        idTweet = row[1]
        selected = row[2]
        if selected == 0:		#TODO: change to if selected == 1:
            selectedTweets.append(idTweet)

    command = "DELETE FROM tweets_annotation.candidate_for_selection where selectedForAttribution=0 and idRun= " + str(run.id) + ";"
    cur.execute(command)
    db.commit()

    random.shuffle(selectedTweets)
    print >> sys.stderr, "6"
    #define control group and save annotations: select 10%
    threshold = 0 #int(math.floor(0.1*len(selectedTweets)))
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
            command = "SELECT count(*) FROM tweets_annotation.annotation where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            print >> sys.stderr, "e"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]
            print >> sys.stderr, "f"
            if count1 == 0:		#item not in database yet
                #count number of attributions
                command = "SELECT count(*) FROM tweets_annotation.annotation where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]
                print >> sys.stderr, "g"
                if attributions < campaign.numberAnnotations:	#verify if it does not exceed threshold
                    command = "insert into tweets_annotation.annotation (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)
        db.commit()
        print >> sys.stderr, "f"
        #assign tweet to all one-shot users
        for user in one_shot_users:
            command = "SELECT count(*) FROM tweets_annotation.annotation_one_shot where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]

            if count1 == 0:		#item not in database yet
                command = "SELECT count(*) FROM tweets_annotation.annotation_one_shot where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]

                if attributions < campaign.numberAnnotations:	#verify if it does not exceed threshold
                    command = "insert into tweets_annotation.annotation_one_shot (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)
        db.commit()

        counter = counter + 1
    print >> sys.stderr, "7"
    #make attributions from remaining tweets and save annotations (if threshold has not been surpassed so far)
    for tweet in selectedTweets:
        length_users = len(users) + len(one_shot_users)
        rdm = int(random.random()*length_users)
        tmp = len(users) - 1
        if rdm > tmp:	#select one_shot_user and reserve special annotation
            new_rdm = rdm - len(users)
            user = one_shot_users[new_rdm]

            command = "SELECT count(*) FROM tweets_annotation.annotation_one_shot where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]

            if count1 == 0:		#item not in database yet
                command = "SELECT count(*) FROM tweets_annotation.annotation_one_shot where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]

                if attributions < campaign.numberAnnotations:	#verify if it does not exceed threshold
                    command = "insert into tweets_annotation.annotation_one_shot (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)

        else:
            user = users[rdm]

            command = "SELECT count(*) FROM tweets_annotation.annotation where idTweet = " + str(tweet) + " and idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
            cur.execute(command)
            for row in cur.fetchall():
                count1 = row[0]

            if count1 == 0:		#item not in database yet
                command = "SELECT count(*) FROM tweets_annotation.annotation where idRun = " + str(run.id) + " and idUser =" + str(user.id) + ";"
                cur.execute(command)
                for row in cur.fetchall():
                    attributions = row[0]

                if attributions < campaign.numberAnnotations:	#verify if it does not exceed threshold
                    command = "insert into tweets_annotation.annotation (idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
                    cur.execute(command)
    """
    db.commit()
    print >> sys.stderr, "7"

    for tweet in tweets:
        for user in users:
            command = "insert into tweets_annotation.annotation(idUser,idTweet,idRun) values (" + str(user.id) + "," + str(tweet) + "," + str(run.id) + ");"
            cur.execute(command)


    #update run status
    cur = db.cursor()
    command = "UPDATE tweets_annotation.run SET status = " + '"' + "active" + '"' + " where idRun = " + str(run.id) + ";"
    cur.execute(command)
    cur.connection.commit();
    print >> sys.stderr, "9"

    #send email
    sendEmail("Your account was selected to start a new annotation run.\nPlease visit reaction.fe.up.pt/annotation and login with your credentials.", "New annotation run", users)

