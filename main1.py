import webapp2
import jinja2
import os
import StringIO
import json
import urllib
import logging
import time

from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import urlfetch

API_KEY = "AIzaSyBRihR54P1jG7ibkBmito879LZ4ZdiQiuo"


env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def parse_resume(type):
    current_user = users.get_current_user()
    current_email = current_user.email()
    current_profile = Profile.query().filter(Profile.email == current_email).get()
    resume = current_profile.resume
    if type is ' ' :
        resume = resume.replace('\n','').replace('\r','').lower()
        wordArray = resume.split(type)
    else:
        #resume = resume.replace('\r', '\n')
        wordArray = resume.split(type)
    return wordArray
    #split resume by line, look for consistency

def find_action_words():
    action_match = {}
    words = parse_resume(' ')
    action_count = 0
    for word in words:
        if word in action_words:
            for action_word in action_words:
                if word == action_word and word not in action_match:
                    action_match[word] = 1
                    action_count += 1
                elif word == action_word:
                    action_match[word] += 1
                    action_count += 1
        else:
            pass
    action_match['count'] = action_count
    return action_match

def find_dead_words():
    dead_match = {}
    words = parse_resume(' ')
    dead_count = 0
    for word in words:
        if word in dead_words:
            for dead_word in dead_words:
                if word == dead_word and word not in dead_match:
                    dead_match[word] = 1
                    dead_count += 1
                elif word == dead_word:
                    dead_match[word] += 1
                    dead_count += 1
        else:
            pass
    dead_match['count'] = dead_count
    return dead_match

def analyze_entities():
    resume = parse_resume('\n')
    linenum = 1
    joblines = []

    for resume_line in resume:
        data = {
         "document": {
            "type": "PLAIN_TEXT",
            "language": "EN",
            "content": resume_line,
          },
          "encodingType": "UTF8",
        }

        headers = {
            "Content-Type" : "application/json; charset=utf-8"
        }

        result = urlfetch.fetch(entities_url,
             method=urlfetch.POST,
             payload=json.dumps(data),
             headers=headers
        )

        checkorder = 0
        job_line = 0
        if result.status_code == 200:
            j = json.loads(result.content)
            type_list = []
            for i in range(len(j['entities'])):
                type_list.append(j['entities'][i]['type'])
            #print 'This is the type list: ' + type_list
            for type in type_list:
                print 'Type is: ' + type
                print 'check_order is: ' + str(checkorder)
                if type == 'PERSON' and checkorder == 0:
                    checkorder += 1
                    job_line += 1
                elif type == 'ORGANIZATION' or type == 'OTHER' and checkorder == 1:
                    checkorder += 1
                    job_line += 1
                elif type == 'LOCATION' and checkorder == 2:
                    job_line += 1
            if job_line >= 3:
                joblines.append(linenum)
        else:
            msg = 'Error accessing insight API:'+str(result.status_code)+" "+str(result.content)
        linenum += 1

        #print job_line
    if len(joblines) > 0:
        return joblines
    else:
        return 0


def getCategories(url): #url is unique to categories function in api
    current_user = users.get_current_user()
    current_email = current_user.email()
    current_profile = Profile.query().filter(Profile.email == current_email).get()
    resume = current_profile.resume
    data = {
     "document": {
        "type": "PLAIN_TEXT",
        "language": "EN",
        "content": resume,
      }
    }
    headers = {
        "Content-Type" : "application/json; charset=utf-8"
    }
    jsondata = json.dumps(data)
    result = urlfetch.fetch(url, method=urlfetch.POST, payload=json.dumps(data), headers=headers)
    print result
    python_result = json.loads(result.content)
    print python_result
    string = ""
    if 'categories' in python_result:
        for i in range(0, len(python_result["categories"])):
             string += "Your resume indicates the "
             string += python_result["categories"][i]["name"]
             string += " category with a "
             string += str(python_result["categories"][i]["confidence"])
             string += " level of confidence. \n"
        return string
    else:
        return 'Not enough data'




def getSentiment(url): #url is unique to sentiment function in api
    current_user = users.get_current_user()
    current_email = current_user.email()
    current_profile = Profile.query().filter(Profile.email == current_email).get()
    resume = current_profile.resume
    data = {
        "document": {
        "type": "PLAIN_TEXT",
        "language": "EN",
        "content": resume,
      },
      "encodingType": "UTF32",
    }
    headers = {
    "Content-Type" : "application/json; charset=utf-8"
        }
    jsondata = json.dumps(data)
    result = urlfetch.fetch(url, method=urlfetch.POST, payload=json.dumps(data),  headers=headers)

    python_result = json.loads(result.content)
    string = ""
    if 'documentSentiment' in python_result:
        magnitude = python_result["documentSentiment"]["magnitude"]
        score = python_result["documentSentiment"]["score"]
        if (score < 0.0):
            string = "Your resume has a score of " + str(score) + " out of 1  and a magnitude of " + str(magnitude) + ", which measures the strengh of emotion. This reads as negative"
        elif (score <= .5):
            string = "Your resume has a score of " + str(score) + " out of 1  and a magnitude of " + str(magnitude) + ", which measures the strengh of emotion. This reads as neutral"
        else:
            string = "Your resume has a score of " + str(score) + " out of 1 and a magnitude of " + str(magnitude) + ", which measures the strengh of emotion. This reads as positive"
        return string
    else:
        return 'Not enough data'

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/create', CreateProfile),
    ('/profile', Display_Profile),
    # ('/resume_review', ResumeReview),
    ('/resume_advice', ResumeAdvice),
    ('/upload_resume', ResumeUpload),
    ('/resume', ResumeHandler),
    ('/fail', Login_Fail),
    ('/update', Update_Profile),
    ('/tips', Tips),
], debug=True)



def detect_labels(path):
    """Detects labels in the file."""
    from google.cloud import vision
    import io
    client = vision.ImageAnnotatorClient()

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    response = client.label_detection(image=image)
    labels = response.label_annotations
    print('Labels:')

    for label in labels:
        print(label.description)
