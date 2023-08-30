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
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('agg')
import seaborn as sns
import matplotlib.dates as mdates

#Check to make sure we have an encryption key, if not, it will make one
ef.check_key()

# Create a Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key' # Change this to a strong, random value
app.config['DATABASE'] = 'journal.db'

import os
current_directory = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(current_directory, 'journal.db')
conn = sqlite3.connect(db_path)
# Connect to database
#conn = sqlite3.connect('/journal.db')
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
    #Then we load only those that are in the config file, query that day of data, decrypt and delete those rows
    #reupload that data without the rows, then insert the data from our form
    print('------------------------------------------------')
    print('date to load = ' + str(date_to_load))
    if date_to_load:
        
        date_to_load_query = f"SELECT * FROM journal WHERE for_date = '{date_to_load.strftime('%Y-%m-%d')}'"
        date_to_load_data = pd.read_sql_query(date_to_load_query, conn)
    
        if not date_to_load_data.empty:
            #load data from the specified day into a df
            date_to_load_data = ef.decrypt_df(date_to_load_data, ['entry','value','value_data_type'])
            date_to_load_columns = date_to_load_data.entry.unique()
        else:
        # Get the data from the database using pandas
            latest_query = 'SELECT * FROM journal WHERE for_date = (SELECT MAX(for_date) FROM journal)'
            latest_data = pd.read_sql_query(latest_query, conn)
            latest_data = ef.decrypt_df(latest_data, ['entry','value','value_data_type'])
        
    else:
    # Get the data from the database using pandas
        latest_query = 'SELECT * FROM journal WHERE for_date = (SELECT MAX(for_date) FROM journal)'
        latest_data = pd.read_sql_query(latest_query, conn)
        latest_data = ef.decrypt_df(latest_data, ['entry','value','value_data_type'])

    print('date_to_load_columns: ' + str(date_to_load_columns))
   
    print('latest data: ' + str(latest_data))

    for field_name, field_data in form_fields.items():
        print('field name:' + str(field_name))
        print(field_data)
        if ((field_data['label'] in date_to_load_columns) or (not latest_data.empty)) or latest_data.empty:
            field_type = getattr(wtforms, field_data['type'])
            field_args = {
                'label': field_data['label'],
                'validators': [getattr(wtforms.validators, v['type'])() for v in field_data['validators']],
                'default' : field_data.get('default', None)
                        }
            print(field_args)
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

    #Regardless of what's in the form we're going to include a date selection.  Populate it with a date if we selected one
    #or default to today

    if date_to_load: 
        default_date=date_to_load
    else: 
        default_date=date.today

    print('date to load is: ' + str(date_to_load))
    print('default date is: ' + str(default_date))

    date_field_args = {
        'default': default_date,
        'render_kw': {"class": "form-control"}  # Add the class attribute here
    }
    setattr(DynamicForm, 'selected_date', DateField('selected_date', **date_field_args))

    #we'll use the date to load columns values to find what values we should delete
    return DynamicForm, date_to_load_columns


def create_graph(df):
    # drop wont be needed I jsut have tset data with dupes
    
    print('----------------------------------------------------------------------------------------------------')
    df = df.drop_duplicates()
 
    var_names = df.entry.unique()#df.columns.tolist()
    var_names_types = df[['entry','value_data_type']].drop_duplicates()

    df['for_date'] = pd.to_datetime(df['for_date']).dt.date

    df = df.pivot(index='for_date', columns='entry', values='value').reset_index()
    #df = df.reset_index()
    date_range = pd.date_range(start = min(df.for_date), end = max(df.for_date))
    df.set_index('for_date', inplace=True)
    df = df.reindex(date_range)

    df.reset_index(drop=False, inplace=True)
    df.rename(columns={'index': 'for_date'}, inplace=True)
    # Get the list of variable names
    print('data to graphllloooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo')
    print(df)
    print('hereeeee')
    print(request.form)
    if 'variable' in request.form: #request.method == 'POST':
     
        
        
        # Get the selected variable from the form data
        selected_var = request.form.get('variable')

        print(request.form)
        #print(var_names_types)
        print('hereeeee1')
        print(selected_var)
        print('Var check: ' + str(var_names_types.loc[var_names_types['entry']== selected_var].value_data_type.values))

        if var_names_types.loc[var_names_types['entry']== selected_var].value_data_type.values.tolist()[0] =='Integer':
        #if var_names_types[selected_var]['value_data_type'] == 'Integer':
            df[selected_var] = df[selected_var].fillna(0).astype(int)

        # Create a line plot using seaborn
        fig = plt.figure()
        sns.lineplot(x='for_date', y=selected_var, data=df)
        plt.xlabel('Date')
        plt.ylabel(selected_var)
        plt.title('Line Plot of {}'.format(selected_var))
        plt.tight_layout()
        ax = plt.gca()  # Get the current axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.xticks(rotation=45)
        plt.savefig('static/plot.png')

        
        # Render the HTML template with the plot image
        return var_names
    elif 'Day Quality' in df.columns:
        # Get the selected variable from the form data
        print('hereeeee2')
        #print(df)
        selected_var = 'Day Quality'
        df[selected_var] = df[selected_var].fillna(0).astype(int)
        # Create a line plot using seaborn
        fig = plt.figure()
        sns.lineplot(x='for_date', y=selected_var, data=df)
        plt.xlabel('Date')
        plt.ylabel(selected_var)
        plt.title('Line Plot of {}'.format(selected_var))
        plt.tight_layout()
        ax = plt.gca()  # Get the current axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

        plt.xticks(rotation=45)
        plt.savefig('static/plot.png')
    # If the request method is GET, render the HTML template with the form
        return var_names
    else:
        print('nothing to graph')
        return []
     
@app.route('/', methods=['GET', 'POST'])
def form():

    #create an empty variable to add a message to submit to user
    message = ''

    #check get, and then the form for the selected date, if neither are set default to todays date

    if request.args.get('selected_date'):
        
        raw_date = request.args.get('selected_date')
        selected_date = datetime.strptime(raw_date, '%Y-%m-%d')  # Convert string to datetime  

    elif request.form.get('selected_date'):

        selected_date = datetime.strptime(request.form.get('selected_date'), '%Y-%m-%d') 
  
    else:
        selected_date = date.today()

    dynamic_form_class, columns_to_delete= create_form_class(form_fields, date_to_load=selected_date)
    form = dynamic_form_class(request.form)

    if request.method == 'POST':
        # datetime object containing current date and time
        now = datetime.strftime(datetime.now(), "%Y-%m-%d, %H:%M:%S")
        
        #connect to the db and check if there is an entry for today.  If there is delete it and insert the current values
        conn = sqlite3.connect('journal.db')        
        c = conn.cursor()
  
        #first query the rows for our day
        df_to_delete_rows_query = f"SELECT * FROM journal WHERE for_date = '{selected_date.strftime('%Y-%m-%d')}'"
        df_to_delete_rows = pd.read_sql_query(df_to_delete_rows_query, conn)

        #decrypt the df and drop the columns that are currently editable in our config file, delete all of that day
        # ', leave the rest alone and ureupload it
        decrypted_df = ef.decrypt_df(df_to_delete_rows, ['entry','value','value_data_type'])

        decrypted_df_reupload = decrypted_df.drop(decrypted_df[decrypted_df['entry'].isin(columns_to_delete)].index)
        enrypted_df_reupload = ef.encrypt_df(decrypted_df_reupload, ['entry','value','value_data_type'])
        delete_query = f"DELETE FROM journal WHERE for_date = '{selected_date.strftime('%Y-%m-%d')}'"
        #print("delete query run: " + str(delete_query))
        c.execute(delete_query)   
        enrypted_df_reupload.to_sql('journal', conn, if_exists='append', index=False)
        conn.commit()

        for field in form: 
            #print('---------')
            #print(field.name)
            #check if the values name is in the form, and there is data for it.  
            #csrf token gets automatically passed so we dont want that or our selected date because we use that for the field
            #finally this last if is to check if the field name is one of the columns we deleted for editing a day or has no information as in a new day
            if field.name in form and field.data  and field.name != 'csrf_token' and field.name != 'selected_date' and (field.name in columns_to_delete or not columns_to_delete) :
                try:
                    
                    c = conn.cursor()
                    row_insert_query = f"INSERT INTO journal (date_time_stamp, for_date, entry, value, value_data_type) VALUES ({str(datetime.now())}, {selected_date.date()}, {ef.encrypt_value(field.name)},{ef.encrypt_value(field.data)},{ef.encrypt_value(form_fields[field.name]['value_data_type'])})"
                    #print('row insert query: ' + str(row_insert_query))
                    c.execute("INSERT INTO journal (date_time_stamp, for_date, entry, value, value_data_type) VALUES (?, ?, ?, ?,?)", (str(datetime.now()),selected_date.date(),ef.encrypt_value(field.name), ef.encrypt_value(field.data), ef.encrypt_value(form_fields[field.name]['value_data_type'])))
                    conn.commit()
                except:
                    print('issue with: ' + field.name)

        conn.close()
        message = 'Data uploaded for: ' + str(selected_date)
    else:
        pass
    #get the value for how each number valued has be trending up of down
    trend_dict = af.get_trending_dictionary()
    
    graph_var_names = create_graph(af.get_x_days_data(7))
    print('hereeeeej')

    return render_template('index.html', form=form, result_message = message, trend_dict=trend_dict, selected_date = selected_date, var_names = graph_var_names)

if __name__ == '__main__':
    app.run()


