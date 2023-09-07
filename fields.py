from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'database.db'


conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute( """CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry TEXT NOT NULL,
    type TEXT NOT NULL,
    default_type TEXT,
    choices TEXT
);"""
)
conn.close()

# Define a form for editing and adding rows
class EntryForm(FlaskForm):
    entry = StringField('Entry', validators=[DataRequired()])
    type = SelectField('Type', choices=[('SelectField', 'SelectField'), ('RadioField', 'RadioField'), ('StringField', 'StringField'), ('TextAreaField', 'TextAreaField'), ('Boolean', 'Boolean')])
    default_type = SelectField('Default Value',choices=[('Empty', 'Empty'), ('Default Value', 'Default Value'), ('Load Previous Value', 'Load Previous Value')] )
    choices = StringField('Choices')

# Helper function to fetch data from the database
def get_entries():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    entries = cursor.fetchall()
    print(entries)
    print('here1')
    conn.close()
    return entries

# Route for the home page, displaying the table of entries
@app.route('/')
def index():
    entries = get_entries()
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
    form = EntryForm(data={'entry': entry[1], 'type': entry[2], 'default_type': entry[3], 'choices': entry[4]})

    if form.validate_on_submit():
        # Update the entry in the database
        data = form.data
        cursor.execute("UPDATE entries SET entry=?, type=?, default_type=?, choices=? WHERE id=?", (
            data['entry'], data['type'], data['default_type'], data['choices'], id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', form=form)

# Route for adding a new entry
@app.route('/add', methods=['GET', 'POST'])
def add():
    form = EntryForm()

    if form.validate_on_submit():
        data = form.data
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO entries (entry, type, default_type, choices) VALUES (?, ?, ?, ?)",
                       (data['entry'], data['type'], data['default_type'], data['choices']))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)



#add logic to make choices None if there it is no select or radiofield