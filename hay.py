import sys
sys.path.append('/inc')
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, StringField, IntegerField, SelectField, TextAreaField, BooleanField, SubmitField, RadioField 
from wtforms.validators import DataRequired, Email, Optional, NumberRange
import wtforms.validators
import sqlite3
from datetime import date
import json
from datetime import datetime, date
import inc.analysis_functions as af
import inc.encryption_functions as ef
import pandas as pd

#Check to make sure we have an encryption key, if not, it will make one
ef.check_key()

# Create a Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key' # Change this to a strong, random value
app.config['DATABASE'] = 'journal.db'

# Connect to database
conn = sqlite3.connect('journal.db')
c = conn.cursor()

# Create table if it does not exist
c.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, date_time_stamp TEXT, for_date TEXT, entry TEXT, value TEXT, value_data_type TEXT)''')

conn.close()

#Import the json config file that defines the form entries
with open('config.json') as f:
    form_fields = json.load(f)

#Dynamically generate a form based on the Json file
def create_form_class(form_fields, date_to_load):
    date_to_load_columns=[]
    latest_data=pd.DataFrame()
    #Connect to database
    conn = sqlite3.connect('journal.db', check_same_thread=False)
    c = conn.cursor()
    #Create empty form
    class DynamicForm(FlaskForm):
        pass
    #Basic logic we're going for. If there aren't any entries for that day, load everything like a normal day
    #If there is an entry, we go through each of the entry names and see if it is in our config file
    #Then we load only those that are in the config file
    print('------------------------------------------------')
    print('date to load = ' + str(date_to_load))
    if date_to_load:

        date_to_load_query = f"SELECT * FROM journal WHERE for_date = '{date_to_load.strftime('%Y-%m-%d')}'"
        #print(date_to_load_query)
        date_to_load_data = pd.read_sql_query(date_to_load_query, conn)
        #print('date to load: ' + str(date_to_load))
        print(1111111111111111111)

        if not date_to_load_data.empty:
            print('222222222222222222 ' + str(date_to_load))
            #load data from the specified day into a df
            date_to_load_data = ef.decrypt_df(date_to_load_data, ['entry','value','value_data_type'])
            date_to_load_columns = date_to_load_data.entry.unique()
           # print('there is data to load for this day')
        else:
            print('33333333333333333333')
        # Get the data from the database using pandas
            latest_query = 'SELECT * FROM journal WHERE for_date = (SELECT MAX(for_date) FROM journal)'
            latest_data = pd.read_sql_query(latest_query, conn)
            latest_data = ef.decrypt_df(latest_data, ['entry','value','value_data_type'])
            #print('there is no data, time to use the defaults')
        
    else:
        print(444444444444444444444444444)
    # Get the data from the database using pandas
        latest_query = 'SELECT * FROM journal WHERE for_date = (SELECT MAX(for_date) FROM journal)'
        latest_data = pd.read_sql_query(latest_query, conn)
        latest_data = ef.decrypt_df(latest_data, ['entry','value','value_data_type'])
        #print('there is no data, time to use the defaults')


    print('date_to_load_columns: ' + str(date_to_load_columns))
   
    print('latest data: ' + str(latest_data))

    for field_name, field_data in form_fields.items():
        
        if ((field_data['label'] in date_to_load_columns) or (not latest_data.empty)):
            field_type = getattr(wtforms, field_data['type'])
            field_args = {
                'label': field_data['label'],
                'validators': [getattr(wtforms.validators, v['type'])() for v in field_data['validators']],
                'default' : field_data.get('default', None)
                        }

            if date_to_load and not date_to_load_data.empty:
                print(date_to_load_data.loc[date_to_load_data['entry']==field_data['label'], 'value'].values[0]   )
                field_args['default'] = date_to_load_data.loc[date_to_load_data['entry']==field_data['label'], 'value'].values[0]
            elif field_data.get('load_previous_value', None):
                c.execute("SELECT value FROM journal WHERE entry=? ORDER BY id DESC LIMIT 1", (field_data['label'],))
                row = c.fetchone()
                if row != None:
                    #print(row[0])
                    field_args['default'] = row[0]

            #We need to seperate Select and Radio fields because they have a choice field 
            if field_data['type'] == 'SelectField' or field_data['type'] == 'RadioField':
                field_args['choices'] = [(k, v) for k, v in field_data['choices'][0].items()]

            #Create field and add to form
            field = field_type(**field_args)
            setattr(DynamicForm, field_name, field)
    conn.close()

    #Regardless of what's in the form we're going to include a date selection

    if date_to_load: 
        default_date=date_to_load
    else: 
        default_date=date.today

    print('date to load is: ' + str(date_to_load))
    print('default date is: ' + str(default_date))
    #setattr(DynamicForm, 'selected_date',  DateField('selected_date', default=default_date, render_kw={"class": "form-control"}))
    date_field_args = {
        'default': default_date,
        'render_kw': {"class": "form-control"}  # Add the class attribute here
    }
    setattr(DynamicForm, 'selected_date', DateField('selected_date', **date_field_args))


    return DynamicForm, date_to_load_columns
 


@app.route('/', methods=['GET', 'POST'])
def form():

    print('FOOOOOOOOOORRRRRRRRRRRRRRRRRMMMMMMMMMMMMMMMMMMMMMMMMM')
    #create an empty variable to add a message to submit to user
    message = ''

    #check to see if a data was selected to pass it to the form creation function
    #selected_date=None


    if request.args.get('selected_date'):
        
        raw_date = request.args.get('selected_date')
        selected_date = datetime.strptime(raw_date, '%Y-%m-%d')  # Convert string to datetime    
        #selected_date = selected_date.strftime('%Y-%m-%d') 
        print('raw date: ' + str(raw_date))  
    elif request.form.get('selected_date'):
        selected_date = datetime.strptime(request.form.get('selected_date'), '%Y-%m-%d') 
        print('get date: ' +  str(selected_date))
  
    else:
        selected_date = date.today()
        print('todays date')

    #if request.method == 'POST' and getattr(getattr(form, 'selected_date'), 'data')  :
     #   selected_date = getattr(getattr(form, 'selected_date'), 'data')  
    #    print('Selected date from POST: ' + str(selected_date))

    #print('request form get: ' + str(request.form.get('selected_date')))
    #form, columns_to_update = create_form_class(form_fields, date_to_load=selected_date)()
    dynamic_form_class, columns_to_delete= create_form_class(form_fields, date_to_load=selected_date)
    form = dynamic_form_class(request.form)
    print('columns to delete: ' + str(columns_to_delete))
    print(selected_date)
    #if request.method == 'POST':
    #    selected_date = getattr(getattr(form, 'selected_date'), 'data')  
    #    print('Selected date from POST: ' + str(selected_date))
   # else:
   #     selected_date=None
   #     print('Selected date is: ' + str(selected_date))

    #print(dir(form))
    if request.method == 'POST':
        # datetime object containing current date and time
        now = datetime.strftime(datetime.now(), "%Y-%m-%d, %H:%M:%S")
        
        #connect to the db and check if there is an entry for today.  If there is delete it and insert the current values
        conn = sqlite3.connect('journal.db')        
        c = conn.cursor()
        print("Raw POST data:", request.data)
  
        #check to see if the submitted date is different from today, if it is, delete the entry from that day
        #the entry will have the date time stamp it was submitted on and the submitted date will be the day it is for
        df_to_delete_rows_query = f"SELECT * FROM journal WHERE for_date = '{selected_date.strftime('%Y-%m-%d')}'"
        
        df_to_delete_rows = pd.read_sql_query(df_to_delete_rows_query, conn)
        decrypted_df = ef.decrypt_df(df_to_delete_rows, ['entry','value','value_data_type'])
        #print(date_to_load_query)
        print('dddddddddddddddddddddddddddddddd')
        decrypted_df_reupload = decrypted_df.drop(decrypted_df[decrypted_df['entry'].isin(columns_to_delete)].index)
        enrypted_df_reupload = ef.encrypt_df(decrypted_df_reupload, ['entry','value','value_data_type'])
        print('decrypted_df_upload:') 
        print(decrypted_df_reupload)
        print('-------------submitted date: ' + str(selected_date))
        delete_query = f"DELETE FROM journal WHERE for_date = '{selected_date.date()}'"
        print('delete query: ' + str(delete_query))
        c.execute(delete_query)   
 
        enrypted_df_reupload.to_sql('journal', conn, if_exists='append', index=False)
        conn.commit()

        #For every field, if it has a value insert it into the tablel..
        for field in form:
            if field.name in form and field.data  and field.name != 'csrf_token' and field.name != 'selected_date' and field.name in (columns_to_delete):
                print(field.name)
                print(field.data)
                c = conn.cursor()
                row_insert_query = f"INSERT INTO journal (date_time_stamp, for_date, entry, value, value_data_type) VALUES ({str(datetime.now())}, {selected_date}.date(), {ef.encrypt_value(field.name)},{ef.encrypt_value(field.data)},{ef.encrypt_value(form_fields[field.name]['value_data_type'])})"
                print('row insert query: ' + str(row_insert_query))
                c.execute("INSERT INTO journal (date_time_stamp, for_date, entry, value, value_data_type) VALUES (?, ?, ?, ?,?)", (str(datetime.now()),selected_date.date(),ef.encrypt_value(field.name), ef.encrypt_value(field.data), ef.encrypt_value(form_fields[field.name]['value_data_type'])))
                conn.commit()


        conn.close()
        message = 'Data uploaded for: ' + str(selected_date)
    else:
        pass

    trend_dict = af.get_trending_dictionary()
    #print(trend_dict)
    return render_template('index.html', form=form, result_message = message, trend_dict=trend_dict, selected_date = selected_date)

if __name__ == '__main__':
    app.run()


