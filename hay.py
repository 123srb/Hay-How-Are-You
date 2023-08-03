from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, IntegerField, SelectField, TextAreaField, BooleanField, SubmitField, RadioField 
from wtforms.validators import DataRequired, Email, Optional, NumberRange
import wtforms.validators
import sqlite3
from datetime import date
import json
from datetime import datetime, date


 

# Create a Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key' # Change this to a strong, random value
app.config['DATABASE'] = 'journal.db'

# Connect to database
conn = sqlite3.connect('journal.db')
c = conn.cursor()

# Create table if it does not exist
c.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, date_time_stamp TEXT, entry TEXT, value TEXT, value_data_type)''')
conn.close()




#Import the json config file that defines the form entries
with open('config.json') as f:
    form_fields = json.load(f)

#Dynamically generate a form based on the Json file
def create_form_class(form_fields):

    #Connect to database
    conn = sqlite3.connect('journal.db', check_same_thread=False)
    c = conn.cursor()
    #Create empty form
    class DynamicForm(FlaskForm):
        pass

    #Iterate though the config file and define the fomr
    for field_name, field_data in form_fields.items():
        field_type = getattr(wtforms, field_data['type'])
        field_args = {
            'label': field_data['label'],
            'validators': [getattr(wtforms.validators, v['type'])() for v in field_data['validators']],
            'default' : field_data.get('default', None)
        }

    #Check to see if we want to load the previous value as the default 
        if field_data.get('load_previous_value', None):
             c.execute("SELECT value FROM journal WHERE entry=? ORDER BY id DESC LIMIT 1", (field_data['label'],))
             row = c.fetchone()
             if row != None:
                field_args['default'] = row[0]
                #default_val = row[0]

        #We need to seperate Select and Radio fields because they have a choice field 
        if field_data['type'] == 'SelectField' or field_data['type'] == 'RadioField':
            field_args['choices'] = [(k, v) for k, v in field_data['choices'][0].items()]

        #Create field and add to form
        field = field_type(**field_args)
        setattr(DynamicForm, field_name, field)
    conn.close()

    return DynamicForm
 

@app.route('/', methods=['GET', 'POST'])
def form():
    message = ''
    
    form = create_form_class(form_fields)()
    print(dir(form))
    if request.method == 'POST':
        # datetime object containing current date and time
        now = datetime.strftime(datetime.now(), "%Y-%m-%d, %H:%M:%S")
        
        # Handle form submission
        #data = {}

        #connect to the db and check if there is an entry for today.  If there is delete it and insert the current values
        conn = sqlite3.connect('journal.db')        
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM journal WHERE DATE(date_time_stamp) = DATE(DATETIME('now', '-10 hours' ) )  LIMIT 1")
        is_entry = c.fetchone()
   
        if is_entry[0] > 0:
            print('here')
            #print(is_entry)
            today = date.today()
            print(today)
            delete_query = f"DELETE FROM journal WHERE DATE(date_time_stamp) = Date({today})"
            c.execute(delete_query)
            #c.execute("DELETE FROM journal WHERE DATE(date_time_stamp) = DATE(DATETIME('now', ' -10 hours' ) )")
            conn.commit()
          
        #For every field, if it has a value insert it into the table
        for field in form:
            print(field)
            if field.name in form and field.data  and field.name != 'csrf_token':
                c = conn.cursor()
                c.execute("INSERT INTO journal (date_time_stamp, entry, value, value_data_type) VALUES (DATETIME('now', '-10 hours' ), ?, ?,?)", (field.name, field.data, form_fields[field.name]['value_data_type']))
                conn.commit()

        conn.close()
        message = 'Data uploaded for: ' + (now)
    trend_dict = {'Day Quality': 9.0, 'Work Stress': 0.0, 'Meditation': 7.0, 'Creativity': 4.0, 'Energy': 0.0}
    return render_template('index.html', form=form, result_message = message, trend_dict=trend_dict)

if __name__ == '__main__':
    app.run()


