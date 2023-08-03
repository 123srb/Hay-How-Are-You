import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
import numpy as np

result_dict = {}   
    
# Connect to the SQLite database
conn = sqlite3.connect('journal.db')
cursor = conn.cursor()

# Define the SQL query to select all columns from the table
sql_query = 'SELECT * FROM journal WHERE DATETIME(date_time_stamp) BETWEEN DATETIME("now", "-180 days") and DATETIME()'


# Get the data from the database using pandas
df = pd.read_sql_query(sql_query, conn)

df['date'] = pd.to_datetime(df['date_time_stamp']).dt.date 
df['date_time_stamp'] = pd.to_datetime(df['date_time_stamp'])

df = df[df['value_data_type'].isin(['Integer','Binary'])]

variable_names = df.entry.unique()

for name in variable_names:
    df_var = df[df['entry']==name]

    df_var = df_var.sort_values(by='date_time_stamp', ascending= True).reset_index(drop=True)
    df_var['date_var'] = df_var.index

    x = df_var[['date_var']]
    y = df_var['value'] 

    model = LinearRegression()
    model.fit(x,y)
    slope = model.coef_[0]
    result_dict[name] = slope

print(result_dict)
