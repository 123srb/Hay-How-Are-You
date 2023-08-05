import sqlite3
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from flask import Flask, render_template, request
from wtforms import DecimalField, StringField, IntegerField, SelectField, TextAreaField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email, Optional, NumberRange




app = Flask(__name__)
form_config = {
    'Journal Entry': {
        'type': TextAreaField,
        'label': 'Journal Entry',
        'validators': [DataRequired()],
        'value_data_type': 'String' 
    },
    'Day Quality': {
        'type': SelectField,
        'label': 'Day Quality',
        'choices': [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10')],
        'load_previous_value': True,
        'validators': [DataRequired()],
        'value_data_type': 'Integer' 
    },
    'Work Stress': {
        'type': SelectField,
        'label': 'Work Stress',
        'choices': [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10')],
        'load_previous_value': True,
        'validators': [DataRequired()],
        'value_data_type': 'Integer' 
    },
      'Mood Majora': {
        'type': SelectField,
        'label': 'Mood Majora',
        'choices':     [('Admiration','Admiration')
    ,('Adoration','Adoration')
    ,('Aesthetic appreciation','Aesthetic appreciation')
    ,('Amusement','Amusement')
    ,('Anxiety','Anxiety')
    ,('Awe','Awe')
    ,('Awkwardness','Awkwardness')
    ,('Boredom','Boredom')
    ,('Calmness','Calmness')
    ,('Confusion','Confusion')
    ,('Craving','Craving')
    ,('Disgust','Disgust')
    ,('Empathetic pain','Empathetic pain')
    ,('Entrancement','Entrancement')
    ,('Envy','Envy')
    ,('Excitement','Excitement')
    ,('Fear','Fear')
    ,('Frustration','Frustration')
    ,('Horror','Horror')
    ,('Interest','Interest')
    ,('Joy','Joy')
    ,('Nostalgia','Nostalgia')
    ,('Romance','Romance')
    ,('Sadness','Sadness')
    ,('Satisfaction','Satisfaction')
    ,('Sexual desire','Sexual desire')
    ,('Sympathy','Sympathy')
    ,('Triumph','Triumph')],
        #'load_previous_value': True,
        'validators': [Optional()],
        'value_data_type': 'String' 

    },  

    'Word Of Day': {
        'type': StringField,
        'label': 'Word Of Day',
        'validators': [Optional()],
        'value_data_type': 'String' 
    },
    'Meditation': {
        'type': RadioField,
        'label': 'Meditation',
        'choices': [('0', 'No'), ('1', 'Yes')],
        'validators': [Optional()],
        'default': '0' ,
        'value_data_type': 'Binary' 
    },
        'Stretch': {
        'type': RadioField,
        'label': 'Stretch',
        'choices': [('0', 'No'), ('1', 'Yes')],
        'validators': [Optional()],
        'default': '0' ,
        'value_data_type': 'Binary' 
    },
    'DosageM': {
        'type': StringField,
        'label': 'DosageM',
        'default': '0',
        'validators': [Optional()],
        'value_data_type': 'Integer' 
        
    },
    'DosageMJ': {
        'type': StringField,
        'label': 'DosageMJ',
        
        'validators': [Optional()],
        'default': '0',
        'value_data_type': 'Integer' 
    },
    'Creativity': {
        'type': RadioField,
        'label': 'Creativity',
        'load_previous_values': True,
        'choices':[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'validators': [Optional()],
        'value_data_type': 'Integer' 
    },
        'Energy': {
        'type': RadioField,
        'label': 'Energy',
        'load_previous_values': True,
        'choices':[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'validators': [Optional()],
        'value_data_type': 'Integer' 
    },
    'Ideation': {
        'type': RadioField,
        'label': 'Ideation',
        'choices': [('0', 'No'), ('1', 'Yes')],
        'validators': [Optional()],
        'default': '0' ,
        'value_data_type': 'Binary' 
    },
        'Brain Fog': {
        'type': RadioField,
        'label': 'Brain Fog',
        'load_previous_values': True,
        'choices':[('bad', 'Bad'), ('ok', 'Ok'), ('great', 'Great')],
        'validators': [Optional()],
        'value_data_type': 'String' 
    },
        'Saw Friends': {
        'type': RadioField,
        'label': 'Saw Friends',
        'default': '0',
        'choices':[('0', 'No'), ('1', 'Yes')],
        'validators': [Optional()],
        'value_data_type': 'Binary' 
    },
        'Health': {
        'type': SelectField,
        'label': 'Health',
        'choices': [('Ill', 'Ill'),('Injured', 'Injured'), ('Not Feeling well', 'Not feeling well'), ('A-ok', 'A-ok')],
        'load_previous_value': True,
        'validators': [DataRequired()],
        'value_data_type': 'String' 
    },
        'Ailment': {
        'type': StringField,
        'label': 'Ailment',
       
        'load_previous_value': True,
        'validators': [DataRequired()],
        'value_data_type': 'String' 
    },
}

# Connect to the SQLite database
conn = sqlite3.connect('journal.db')
cursor = conn.cursor()

# Define the SQL query to select all columns from the table
sql_query = 'SELECT * FROM journal'

# Get the data from the database using pandas
df = pd.read_sql_query(sql_query, conn)

df['date'] = pd.to_datetime(df['date_time_stamp']).dt.date
print(df)
