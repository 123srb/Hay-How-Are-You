from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, IntegerField, SelectField, TextAreaField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email, Optional, NumberRange
import wtforms.validators
import sqlite3
from datetime import date
import json

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


#Connect to database
conn = sqlite3.connect('journal.db')
c = conn.cursor()

#Import the json config file that defines the form entries
with open('config.json') as f:
    form_fields = json.load(f)

#Dynamically generate a form based on the Json file
def create_form_class(form_fields):
    #Create empty form
    class DynamicForm(FlaskForm):
        pass

    #Iterate though the config file and define the fomr
    for field_name, field_data in form_fields.items():
        field_type = getattr(wtforms, field_data['type'])
        field_args = {
            'label': field_data['label'],
            'validators': [getattr(wtforms.validators, v['type'])() for v in field_data['validators']]
        }

        #We need to seperate Select and Radio fields because they have a choice field 
        if field_data['type'] == 'SelectField' or field_data['type'] == 'RadioField':
            field_args['choices'] = [(k, v) for k, v in field_data['choices'][0].items()]

        #Create field and add to form
        field = field_type(**field_args)
        setattr(DynamicForm, field_name, field)

    return DynamicForm
 
conn.close()

@app.route('/', methods=['GET', 'POST'])
def form():

    
    form = create_form_class(form_fields)()
    print(dir(form))
    if request.method == 'POST':

        # Handle form submission
        #data = {}

        #connect to the db and check if there is an entry for today.  If there is delete it and insert the current values
        conn = sqlite3.connect('journal.db')        
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM journal WHERE DATE(date_time_stamp) = DATE(DATETIME('now', '-10 hours' ) )  LIMIT 1")
        is_entry = c.fetchone()
        if is_entry[0] > 0:
            print(is_entry)
            c.execute("DELETE FROM journal WHERE DATE(date_time_stamp) = DATE(DATETIME('now', ' -10 hours' ) )")
            conn.commit()
          
        #For every field, if it has a value insert it into the table
        for field in form:
            print(field)
            if field.name in form and field.data and field.name != 'csrf_token':
                c = conn.cursor()
                c.execute("INSERT INTO journal (date_time_stamp, entry, value, value_data_type) VALUES (DATETIME('now', '-10 hours' ), ?, ?,?)", (field.name, field.data, form_fields[field.name]['value_data_type']))
                conn.commit()

        conn.close()
    return render_template('index.html', form=form)

if __name__ == '__main__':
    app.run()


