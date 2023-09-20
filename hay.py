import sys
sys.path.append('/inc')
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash, session
from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, StringField, IntegerField, SelectField, TextAreaField, BooleanField, SubmitField, RadioField, validators
from wtforms.validators import DataRequired, Email, Optional, NumberRange, ValidationError
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
import os
import re
from wtforms.widgets import CheckboxInput

class CheckmarkWidget(CheckboxInput):
    def __call__(self, field, **kwargs):
        if field.data:
            # If the field is True, render a checkmark
            return super(CheckmarkWidget, self).__call__(field, checked=True, **kwargs)
        else:
            # If the field is False, render an empty field
            return super(CheckmarkWidget, self).__call__(field, checked=False, **kwargs)



#Check to make sure we have an encryption key, if not, it will make one
ef.check_key()

# Create a Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key' # Change this to a strong, random value
app.config['DATABASE'] = 'journal.db'

with app.app_context():
    #create the path to where the file is, and create the database if it doesn't exist
    current_directory = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(current_directory, app.config['DATABASE'])
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create journal if it does not exist
    c.execute('''CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY, 
            date_time_stamp TEXT, 
            for_date TEXT, 
            entry TEXT, 
            value TEXT, 
            value_data_type TEXT)''')

    c.execute( """CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry TEXT NOT NULL,
        type TEXT NOT NULL,
        variable_type TEXT NOT NULL,
        default_type TEXT,
        default_value TEXT,
        choices TEXT, 
        active INTEGER DEFAULT 1,
        form_order INTEGER );""")

    conn.close()


# Define a form for editing and adding rows
class EntryForm(FlaskForm):
    entry = StringField('Entry', validators=[DataRequired()])
    type = SelectField('Type', choices=[('StringField', 'StringField'), ('TextAreaField', 'TextAreaField'), ('BooleanField', 'BooleanField'), ('SelectField', 'SelectField'), ('RadioField', 'RadioField'), ('IntegerField', 'IntegerField'), ('DecimalField', 'DecimalField')])
    variable_type = SelectField('Variable Type', choices=[('String', 'Text'), ('Binary', 'Yes or No'), ('Integer', 'Numeric')] ) 
    default_type = SelectField('Default Type',  choices=[('Empty', 'Empty'), ('Default Value', 'Default Value'), ('Load Previous Value', 'Load Previous Value')] )
    default_value = StringField('Default Value')
    choices = StringField('Choices')

def check_entry_data(data):
#Add some error checking
#Check to make sure Select and Radio Fields have a correct number items in their choices and that the variable type matches
    message = ''
    if data['type'] in ['SelectField', 'RadioField']:
        try: 
            choices_list_tuple_list = ast.literal_eval(data['choices'])
            if all(isinstance(item, tuple) and len(item) == 2 for item in choices_list_tuple_list):
                pass
            else:
                message = 'Sorry, but this does not to be in the right format, please look over the choices below and try again'
                return message
        except:
            message = 'Sorry, but this does not to be in the right format, please look over the choices below and try again'
            return message
        pattern = r"\([^)]+\)(?!\s*,\s*\()"
        if re.search(pattern, ''.join(data['choices'].split())):
            pass
        else:
            message = f"check the formating of your choices"

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

        if data['default_type'] == 'Default Value':
            default_value_in_choices = False
            for tup in choices_list_tuple_list:
     
              if tup[0] == data['default_value']:
                  default_value_in_choices = True
            if default_value_in_choices == False:
                message = 'Your default value is not one of the options in your choices'      

#'Boolean fields Need to be Boolean        
    if data['type'] == 'BooleanField':
        if  (data['default_type']=='Default Value'):
            if (data['default_value'] not in ['1', '0']):
                message = 'Your default value for a Boolean can only be 1 or 0'

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

    if data['default_type']=='Default Value' and data['default_value'] == '':
        message = 'You set that there should be a default value but left the value blank'

    return message

#Dynamically generate a form based on the Json file
def create_form_class(date_to_load):
    #get entries and them format the validators into a list of dicts
    form_fields = af.get_entries(just_active=True)
    #form_fields['validators'] = form_fields['validators'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else None)
    
    #form_fields['choices'] = form_fields['choices'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else None)
    form_fields = form_fields.set_index('entry').to_dict(orient='index' )
    date_to_load_columns=[]
    latest_data=pd.DataFrame()
    
    conn = sqlite3.connect(app.config['DATABASE'], check_same_thread=False)
    c = conn.cursor()
    #Create empty form
    class DynamicForm(FlaskForm):
        pass
    #Basic logic we're going for. If there aren't any entries for that day, load everything like a normal day
    #If there is an entry, we go through each of the entry names and see if it is in our config file
    #Then we load only those that are in the config file, query that day of data, decrypt and delete those rows
    #reupload that data without the rows, then insert the data from our form

    if date_to_load:
        
        date_to_load_query = f"SELECT * FROM journal WHERE for_date = '{date_to_load.strftime('%Y-%m-%d')}'"

        date_to_load_data = pd.read_sql_query(date_to_load_query, conn)
    
        if not date_to_load_data.empty:
            #load data from the specified day into a df
            date_to_load_data = ef.decrypt_df(date_to_load_data, ['entry','value','value_data_type'])
            date_to_load_columns = date_to_load_data.entry.unique()
            print(date_to_load_data)
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

    for field_name, field_data in form_fields.items():
        if ((field_name in date_to_load_columns) or (not latest_data.empty)) or latest_data.empty:
            #Set the default field information for the form
            field_type = getattr(wtforms, field_data['type'])
            field_args = {
                'label': field_name,
                'validators': [DataRequired()],
                'default' : field_data.get('default_value', None)
                        }
            #if there is already an entry for that date, let's use it 
            if date_to_load and not date_to_load_data.empty:
                
                #we will try to set the value based on what currently exists, but there is a fringe case 
                #If a new form entry is added, there is data for the day and the value is in our form_entries
                #but there is no data for that form value so it would be an error
                try:
                    print('loaded')
                    print(field_name)

                    field_args['default'] = date_to_load_data.loc[date_to_load_data['entry']==field_name, 'value'].values[0]
                    print(field_args['default'])
                except:
                    pass
            #if the form field is supposed to load the last value, query it
            elif field_data.get('load_previous_value', None):
                c.execute("SELECT value FROM journal WHERE entry=? ORDER BY id DESC LIMIT 1", (field_name,))
                row = c.fetchone()
                if row != None:
                    print(field_name)
                    print(row[0])
                    print('-------------------')
                    field_args['default'] = row[0]

            #We need to seperate Select and Radio fields because they have a choice field 
            if field_data['type'] == 'SelectField' or field_data['type'] == 'RadioField':
                #adding a little fallback logic hear just in case I missed soemthing and an erroneuous value gets through, otherwise flask will crash
                try:
                    choices_tuple = ast.literal_eval(f"[{field_data['choices']}]")
                except:
                    choices_tuple = [('error','error'),('error','error')]

                field_args['choices'] = choices_tuple

   
                    

                 
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
    message = ''
    entry_settings = af.get_entries()

    #check get, and then the form for the selected date, if neither are set default to todays date
    if request.args.get('selected_date'):
        raw_date = request.args.get('selected_date')
        selected_date = datetime.strptime(raw_date, '%Y-%m-%d')  # Convert string to datetime  
    elif request.form.get('selected_date'):
        selected_date = datetime.strptime(request.form.get('selected_date'), '%Y-%m-%d') 
    else:
        selected_date = date.today()

    dynamic_form_class, columns_to_delete= create_form_class( date_to_load=selected_date)
    form = dynamic_form_class(request.form)

    if request.method == 'POST':
        # datetime object containing current date and time
        now = datetime.strftime(datetime.now(), "%Y-%m-%d, %H:%M:%S")
        
        #connect to the db and check if there is an entry for today.  If there is delete it and insert the current values
        conn = sqlite3.connect(app.config['DATABASE'])        
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
            
            #if field.name in form and field.data  and field.name != 'csrf_token' and field.name != 'selected_date' and (field.name in columns_to_delete or not columns_to_delete) :
            if field.name in form and (field.data or field.type=='BooleanField') and field.name != 'csrf_token' and field.name != 'selected_date':
                try: 
                    c = conn.cursor()
                    row_insert_query = "INSERT INTO journal (date_time_stamp, for_date, entry, value, value_data_type) VALUES (?,?,?,?,?)"
                    values = (str(datetime.now()), selected_date.date(), ef.encrypt_value(field.name),ef.encrypt_value(field.data),ef.encrypt_value(entry_settings[entry_settings['entry'] == field.name]['variable_type'].values[0]))
                    c.execute(row_insert_query, values) 
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
    
    try:
        df = af.pivot_data(af.get_x_days_data(30))
        
        # Check if the DataFrame is empty
        if df.empty:
            return jsonify({'error': 'No data available for the selected period'})
        
        selected_column = request.form['selected_column']
        df.sort_values(by='for_date', ascending=True, inplace=True)
        df['for_date'] = df['for_date'].dt.strftime('%Y-%m-%d')
        
        # Create a Plotly figure
        fig = px.line(df, x='for_date', y=selected_column, title=f'{selected_column} Over Time')
        
        df[selected_column]     

        # Have the chart interpret/order the x-axis correctly
        fig.update_layout(autotypenumbers='convert types', autosize=True)
        
        # Format x-axis
        fig.update_xaxes(
            tickvals=df['for_date'],  # Use the 'for_date' column as tick values
            ticktext=df['for_date']   # Use the 'for_date' column as tick labels
        )

        # Dynamically retrieve Y-axis categories and sort them
        category_order = df[selected_column].unique()
        category_order.sort()  # Sort the categories
        
        # Then, set the categoryorder parameter to match your sorted list
        fig.update_yaxes(categoryorder="array", categoryarray=category_order)
      

        # Convert the figure to JSON
        graph_json = fig.to_json()
        
        return jsonify(graph_json)
    except Exception as e:
        # Handle any unexpected errors gracefully
        return jsonify({'error': str(e)})

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
    message = session.pop('error', '')
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    sql_query = "SELECT * FROM entries ORDER BY form_order"
    # Get the data from the database using pandas
    encrypted_entries = pd.read_sql_query(sql_query, conn) 
    conn.close()


    #decrypted_entries = ef.decrypt_df(encrypted_entries, ['entry','type','variable_type','default_type','default_value','choices'])
    decrypted_entries = af.get_entries()

    return render_template('journal_fields.html', entries=decrypted_entries.values.tolist(), result_message= message)

@app.route('/update_active', methods=['POST'])
def update_active():
    if request.method == 'POST':

        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        # Get the list of entry IDs and their new "active" status from the form
        entry_updates = request.form.getlist('entry_update')
        
        cursor.execute("UPDATE entries SET active=0")
        for entry_id in entry_updates:
            cursor.execute("UPDATE entries SET active=1 WHERE id=?", (entry_id,))  

        conn.commit()
        conn.close()
        form_order = request.form.getlist('form_order')
        entry_id = request.form.getlist('entry_id')

        for order in form_order:
            try:
                order_int = int(order)
                if order_int<1:
                    session['error'] = 'Your from order needs to be > 0'
                    
                    return redirect(url_for('index'))
            except:
              session['error'] = 'Form order values must be integers'
              return redirect(url_for('index'))
        
        if  len(form_order) != len(set(form_order)):
            session['error'] = 'Duplicate form order values are not allowed.'
            return redirect(url_for('index'))
            
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        for id, order in zip(entry_id, form_order):
            cursor.execute("UPDATE entries SET form_order=? WHERE id=?", (order, id,))  


        conn.commit()
        conn.close()

        return redirect(url_for('index'))
@app.route('/add', methods=['GET', 'POST'])
def add():
    form = EntryForm()
    message = ''
    decrypted_entries = af.get_entries()

    current_var_names = decrypted_entries.entry.unique()

    #Get the first unused value to add for the form order, that way we can give things we want to show at the bottom large numbers
    sorted_form_order = sorted(decrypted_entries['form_order'])
    first_unused_order_num = None
    if not sorted_form_order:
        first_unused_order_num = 1
    else:
        for i, value in enumerate(sorted_form_order):
            if value != i + 1:
                first_unused_order_num = i + 1
                break
            else:
                first_unused_order_num = len(sorted_form_order) + 1


    if form.validate_on_submit():
        data = form.data
        
        message = check_entry_data(data)
        data['choices'] = ''.join(data['choices'].split())
        

        if data['entry'] in current_var_names:
            message = 'Sorry, it looks like you already have another variable with this name!'

        if message != '':
            return render_template('add.html', form=form, result_message=message)



        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        query = "INSERT INTO entries (entry, type, variable_type, default_type, default_value, choices, form_order) VALUES (?,?,?,?,?,?,?)"
        values = (ef.encrypt_value(data['entry']),ef.encrypt_value(data['type']), ef.encrypt_value(data['variable_type']), ef.encrypt_value(data['default_type']), ef.encrypt_value(data['default_value']), ef.encrypt_value(data['choices']), first_unused_order_num)
        print(query)
        #cursor.execute("INSERT INTO entries (entry, type, value_data_type, default_type, default_value, choices, form_order) VALUES (?, ?, ?, ?, ?, ?, (SELECT IFNULL(MAX(form_order) + 1, 1) FROM entries))",
        #               (ef.encrypt_value(data['entry']), ef.encrypt_value(data['type']), ef.encrypt_value(data['value_data_type']), ef.encrypt_value(data['default_type']), ef.encrypt_value(data['default_value']), ef.encrypt_value(data['choices'])))
        cursor.execute(query,values)
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add.html', form=form, result_message=message)

# Route for editing an entry
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Fetch the entry to be edited
    cursor.execute("SELECT * FROM entries WHERE id=?", (id,))
    entry = cursor.fetchone()

    if entry is None:
        # Handle the case where the entry with the given ID does not exist
        return redirect(url_for('index')) 

    # Populate the form with existing data
    form = EntryForm(data={'entry': ef.decrypt_value(entry[1]), 'type': ef.decrypt_value(entry[2]), 'variable_type': ef.decrypt_value(entry[3]), 'default_type': ef.decrypt_value(entry[4]), 'default_value': ef.decrypt_value(entry[5]),'choices': ef.decrypt_value(entry[6])})

    if form.validate_on_submit():
        # Update the entry in the database
        data = form.data
        message = ''
        message = check_entry_data(data)

        if message != '':
            return render_template('edit.html', form=form, result_message=message)
        
        cursor.execute("UPDATE entries SET entry=?, type=?, variable_type=?, default_type=?, default_value=?, choices=? WHERE id=?", (
            ef.encrypt_value(data['entry']), ef.encrypt_value(data['type']), ef.encrypt_value(data['variable_type']), ef.encrypt_value(data['default_type']), ef.encrypt_value(data['default_value']), ef.encrypt_value(data['choices']), id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', form=form, entry=entry, entry_id=id)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_entry(id):
    if request.method == 'POST':
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()

        cursor.execute("DELETE FROM entries WHERE id=?", (id,))
        conn.commit()
        conn.close()

        # Return a JSON response to indicate successful deletion
        return redirect(url_for('index'))
        #return render_template('index.html')

        #return jsonify({'message': 'Entry deleted successfully'})

if __name__ == '__main__':
    app.run()


