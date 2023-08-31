import sys
sys.path.append('/inc')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from sklearn.linear_model import LinearRegression
import inc.encryption_functions as ef
from flask import render_template, request

import seaborn as sns

def get_x_days_data(num_days, columns_list=['*']):
# Connect to the SQLite database
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
  
    sql_query = f"SELECT {', '.join(columns_list)} FROM journal WHERE for_date >= '{(date.today()-timedelta(days=num_days)).isoformat()}'"
    # Get the data from the database using pandas
    print(sql_query)
    df = pd.read_sql_query(sql_query, conn)

    if columns_list == ['*']:
        df = ef.decrypt_df(df, ['entry','value','value_data_type'])
    else:
        df = ef.decrypt_df(df, columns_list)
    conn.close()
    return df

def get_trending_dictionary():
    #dict to store our results
    result_dict = {}   
    df = get_x_days_data(14)   
    
    df = df[df['value_data_type'].isin(['Integer','Binary'])]

    #Get all unique variable names in the data frame
    variable_names = df.entry.unique()
    
    for name in variable_names:
        #filter df for one specific entry
        df_var = df[df['entry']==name]

        df_var = df_var.sort_values(by='for_date', ascending= True).reset_index(drop=True)
        df_var['date_var'] = df_var.index

        #perform a linear regression to get the slope of the line, use that for trending 
        x = df_var[['date_var']]
        y = df_var['value'] 

        model = LinearRegression()
        model.fit(x,y)
        slope = model.coef_[0]
        result_dict[name] = round(slope,3)

    return(result_dict)

def pivot_data(df):
    df['for_date'] = pd.to_datetime(df['for_date']).dt.date
    df = df.pivot(index='for_date', columns='entry', values='value').reset_index()
    

    date_range = pd.date_range(start = min(df.for_date), end = max(df.for_date))
    df.set_index('for_date', inplace=True)
    df = df.reindex(date_range)

    df.reset_index(drop=False, inplace=True)
    df.rename(columns={'index': 'for_date'}, inplace=True)

    return df

