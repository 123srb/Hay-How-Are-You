import sys
sys.path.append('/inc')
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
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
import plotly.express as px
import io
import ast


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

DATABASE = 'journal.db'


conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute( """CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry TEXT NOT NULL,
    type TEXT NOT NULL,
    variable_type TEXT NOT NULL,
    default_type TEXT,
    default_value TEXT,
    choices TEXT,
    active INTEGER DEFAULT 1
    
);"""
)
conn.close()

# Define a form for editing and adding rows
class EntryForm(FlaskForm):
    entry = StringField('Entry', validators=[DataRequired()])
    type = SelectField('Type', choices=[('StringField', 'StringField'), ('TextAreaField', 'TextAreaField'), ('BooleanField', 'BooleanField'), ('SelectField', 'SelectField'), ('RadioField', 'RadioField')])
    variable_type = SelectField('Variable Type', choices=[('String', 'Text'), ('Binary', 'Yes or No'), ('Integer', 'Numeric')] ) 
    default_type = SelectField('Default Type',  choices=[('Empty', 'Empty'), ('Default Value', 'Default Value'), ('Load Previous Value', 'Load Previous Value')] )
    default_value = StringField('Default Value')
    choices = StringField('Choices')
# Helper function to fetch data from the database
def get_entries():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    entries = cursor.fetchall()
    conn.close()
    return entries

     
#Import the json config file that defines the form entries
with open('config.json') as f:
    form_fields = json.load(f)

def check_entry_data(data, current_var_names):
#Add some error checking
#Check to make sure Select and Radio Fields have a correct number items in their choices
    message = ''
    if data['entry'] in current_var_names:
        message = 'Sorry, it looks like you already have another variable with this name!'

    if data['type'] in ['SelectField', 'RadioField']:

        try: 
            choices_list_tuple_list = ast.literal_eval(data['choices'])
        except:
            message = 'Sorry, but this does not to be in the right format, please look over the options below and try again'
            return message

        if len(choices_list_tuple_list) <= 1:
            message = 'It looks like you do not have multiple values in your choices, please separate each value with a comma'
            return message

        strings = 0
        numbers = 0
        for tup in choices_list_tuple_list:
            if tup[0].isdigit():
                numbers += 1
            else:
                strings += 1
        if numbers > 0 and strings > 0:
            message = 'It looks like you are combining strings and numbers in your choices, please check the first entry of each option ("first","second")'
        if data['variable_type'] == 'Integer' and strings > 0:
            message = 'It appears that there are string values in your choices, they must match your variable type'

        if data['variable_type'] == 'Binary':
                if len(choices_list_tuple_list) != 2:
                    message = 'You can only have 2 valeus in a binary variable type'
                binary_list = [choices_list_tuple_list[0][0], choices_list_tuple_list[1][0]]
                if binary_list.count(0) != 1 and binary_list.count(1) != 1:
                    message = 'A binary variable has to have a 1 and a 0 in it'




#'Boolean fields Need to be Boolean        
    if data['type'] == 'BooleanField':
        if  (data['default_type']=='Default Value'):
            print(data['default_value'])
            if (data['default_value'] not in ['True', 'False']):
                message = 'Your default value for a Boolean can only be True or False'

#string can't be numbers, but really it would probably still work because strings are numbers by default
    elif data['variable_type'] == 'String':
        if not isinstance(data['default_value'], str):
            message = 'You chose String as your variable type, but your default value is not a variable'

#check if an integer value isn't a number, then check if you can float it, if you can check if it is whole to make an int
    elif data['variable_type'] == 'Integer':
        if (not isinstance(data['default_value'], (int, float))) and  (data['default_type']=='Default Value'):
            try:
                data['default_value'] = float(data['default_value'])
                if data['default_value'].is_integer():
                    data['default_value'] = int(data['default_value'])
            except ValueError:
                message = 'You chose Number as your default value, but this value is a string'
    return message

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


    date_field_args = {
        'default': default_date,
        'render_kw': {"class": "form-control"}  # Add the class attribute here
    }
    setattr(DynamicForm, 'selected_date', DateField('selected_date', **date_field_args))

    #we'll use the date to load columns values to find what values we should delete
    return DynamicForm, date_to_load_columns



     
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

        #decrypt the df and drop the columns that are currently editable in our config file because we are uploading values for them
        # delete all of that day in the table since we have all the values that aren't editable in our dataframe 
        # ', leave the rest alone and ureupload it
        decrypted_df = ef.decrypt_df(df_to_delete_rows, ['entry','value','value_data_type'])

        decrypted_df_reupload = decrypted_df.drop(decrypted_df[decrypted_df['entry'].isin(columns_to_delete)].index)
        enrypted_df_reupload = ef.encrypt_df(decrypted_df_reupload, ['entry','value','value_data_type'])
        delete_query = f"DELETE FROM journal WHERE for_date = '{selected_date.strftime('%Y-%m-%d')}'"
        c.execute(delete_query)   
        enrypted_df_reupload.to_sql('journal', conn, if_exists='append', index=False)
        conn.commit()

        for field in form: 

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
    

    return render_template('index.html', form=form, result_message = message, trend_dict=trend_dict, selected_date = selected_date, columns=af.get_x_days_data(30, ['entry']).entry.unique())



@app.route('/update_graph', methods=['POST'])
def update_graph():

    df = af.pivot_data(af.get_x_days_data(30))
    selected_column = request.form['selected_column']
    df.sort_values(by='for_date', ascending=True, inplace=True)
    df['for_date'] = df['for_date'].dt.strftime('%Y-%m-%d')
    # Create a Plotly figure
    fig = px.line(df, x='for_date', y=selected_column, title=f'{selected_column} Over Time')
    #have the chart interpret/order the x axis correctly
    fig.update_layout(autotypenumbers='convert types', autosize=True)
    #format x axis
    fig.update_xaxes(
    tickvals=df['for_date'],  # Use the 'for_date' column as tick values
    ticktext=df['for_date']   # Use the 'for_date' column as tick labels
    )
    # Convert the figure to JSON
    graph_json = fig.to_json()
    
    return jsonify(graph_json)

@app.route('/download_file')
def download_file():
    # Create a file-like buffer to receive the output only store in ram
    df= af.get_entire_db()
    csv_data = df.to_csv(index=False).encode('utf-8')

    # Create a file-like buffer to hold the CSV data in memory
    output = io.BytesIO()
    output.write(csv_data)
    output.seek(0)
    filename = 'journal_database.csv'

    # Send the file as an attachment with the provided filename
    return send_file(output, as_attachment=True, download_name=filename)

@app.route('/journal_fields')
def index():
    entries = get_entries()
    print(entries)

    return render_template('journal_fields.html', entries=entries)

@app.route('/update_active', methods=['POST'])
def update_active():
    if request.method == 'POST':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Get the list of entry IDs and their new "active" status from the form
        entry_ids = request.form.getlist('entry_update')

        cursor.execute("UPDATE entries SET active=0")
        for entry_id in entry_ids:
            print(entry_id)
            cursor.execute("UPDATE entries SET active=1 WHERE id=?", (entry_id,))  

        conn.commit()
        conn.close()

        return redirect(url_for('index'))
@app.route('/add', methods=['GET', 'POST'])
def add():
    form = EntryForm()
    message = ''

    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    sql_query = "SELECT * FROM entries"
    # Get the data from the database using pandas
    current_entries = pd.read_sql_query(sql_query, conn)
 

    conn.close()

    print(current_entries)
    print('-----------------------------------------------')
    current_var_names = current_entries.entry.unique()

    if form.validate_on_submit():
        data = form.data

        message = check_entry_data(data, current_var_names)

        if message != '':
            return render_template('add.html', form=form, result_message=message)

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO entries (entry, type, variable_type, default_type, default_value, choices) VALUES (?, ?, ?, ?, ?, ?)",
                       (data['entry'], data['type'],data['variable_type'], data['default_type'], data['default_value'], data['choices']))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add.html', form=form, result_message=message)

# Route for editing an entry
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch the entry to be edited
    cursor.execute("SELECT * FROM entries WHERE id=?", (id,))
    entry = cursor.fetchone()

    if entry is None:
        # Handle the case where the entry with the given ID does not exist
        return redirect(url_for('index')) 

    # Populate the form with existing data
    form = EntryForm(data={'entry': entry[1], 'type': entry[2], 'variable_type': entry[3], 'default_type': entry[4], 'default_value': entry[5],'choices': entry[6]})

    if form.validate_on_submit():
        # Update the entry in the database
        data = form.data
        cursor.execute("UPDATE entries SET entry=?, type=?, variable_type=?, default_type=?, default_value=?, choices=? WHERE id=?", (
            data['entry'], data['type'], data['variable_type'], data['default_type'], data['default_value'], data['choices'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', form=form, entry=entry, entry_id=id)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_entry(id):
    print('delee')
    if request.method == 'POST':
        print('delete post')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM entries WHERE id=?", (id,))
        conn.commit()
        conn.close()

        # Return a JSON response to indicate successful deletion
        print('madeittodelete')
        return redirect(url_for('index'))
        #return render_template('index.html')

        #return jsonify({'message': 'Entry deleted successfully'})

if __name__ == '__main__':
    app.run()


