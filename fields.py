from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
import ast


app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'database.db'


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
    variable_type = SelectField('Variable Type', choices=[('Binary', 'Yes or No'), ('Integer', 'Numeric'), ('String', 'Text')] ) 
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

# Route for the home page, displaying the table of entries
@app.route('/')
def index():
    entries = get_entries()
    print(entries)

    return render_template('index.html', entries=entries)

# Route for editing an entry
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch the entry to be edited
    cursor.execute("SELECT * FROM entries WHERE id=?", (id,))
    entry = cursor.fetchone()

    # Populate the form with existing data
    form = EntryForm(data={'entry': entry[1], 'type': entry[2], 'default_type': entry[3], 'default_value': entry[4],'choices': entry[5]})

    if form.validate_on_submit():
        # Update the entry in the database
        data = form.data
        cursor.execute("UPDATE entries SET entry=?, type=?, variable_type=?, default_type=?, default_value=?, choices=? WHERE id=?", (
            data['entry'], data['type'], data['variable_type'], data['default_type'], data['default_value'], data['choices'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', form=form)

# Route for adding a new entry
@app.route('/add', methods=['GET', 'POST'])
def add():
    form = EntryForm()
    message = ''


    if form.validate_on_submit():
        data = form.data

#Add some error checking
#Check to make sure Select and Radio Fields have a correct number items in their choices
        if data['type'] in ['SelectField', 'RadioField']:
            choices_list_tuple_list = ast.literal_eval(data['choices'])

            if len(choices_list_tuple_list) <= 1:
                message = 'It looks like you do not have multiple values in your choices, please separate each value with a comma'

            strings = 0
            numbers = 0
            for tup in choices_list_tuple_list:
                if tup[0].isdigit():
                    numbers += 1
                else:
                    strings += 1
            if numbers > 0 and strings > 0:
                message = 'It looks like you are combining strings and numbers in your choices, please check the first entry of each option ("first","second")'
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
    

if __name__ == '__main__':
    app.run(debug=True)
