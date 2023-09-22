import sys
sys.path.append('/inc')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from sklearn.linear_model import LinearRegression
import inc.encryption_functions as ef
from flask import render_template, request

import seaborn as sns

def get_graph_column_order(num_days, columns_list=['*']):
    #Just a big ol function to get all the entry names that are in the journal, and all the entry names in the entry table and then sort them by form_order
# Connect to the SQLite database
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
  
    journal_query = f"SELECT entry FROM journal as j  WHERE for_date >= '{(date.today()-timedelta(days=num_days)).isoformat()}' GROUP BY entry"
    entry_query = f"SELECT entry, form_order FROM entry"
    # Get the data from the database using pandas
    journal_df = pd.read_sql_query(journal_query, conn)
    entry_df = pd.read_sql_query(entry_df, conn)
    conn.close()
    
    journal_df = ef.decrypt_df(journal_df, ['entry'])
    entry_df = ef.decrypt_df(entry_df, ['entry','form_order'])
    result_df = pd.concat([journal_df, entry_df], ignore_index=True)
    aggregated_df = result_df.groupby('entry')['form_order'].max().reset_index()
    
    ordered_df = pd.concat([aggregated_df[aggregated_df['form_order']>0].sort_values(by='form_order'), aggregated_df[aggregated_df['form_order']==0]], ignore_index=True)

    return ordered_df.entry.unique()

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

def get_entire_db():
   # Connect to the SQLite database
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    sql_query = "SELECT * FROM journal"
    # Get the data from the database using pandas
    df = pd.read_sql_query(sql_query, conn)
    df = ef.decrypt_df(df, ['entry','value','value_data_type'])

    conn.close()

    return df


def get_entries(just_active=False):
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    if just_active == False:
        sql_query = "SELECT * FROM entries ORDER BY form_order"
    else:
        sql_query = "SELECT * FROM entries WHERE active=1 ORDER BY form_order"
    # Get the data from the database using pandas
    encrypted_entries = pd.read_sql_query(sql_query, conn) 
    conn.close()


    decrypted_entries = ef.decrypt_df(encrypted_entries, ['entry','type','variable_type','default_type','default_value','choices'])
    return decrypted_entries

     

def get_trending_dictionary():
    #dict to store our results
    result_dict = {}   
    df = get_x_days_data(14)   
    
    df = df[df['value_data_type'].isin(['Integer','Binary'])]
    df.replace({'False': 0, 'True': 1}, inplace=True)

    #Just in case somehow a string gets through we don't want the whole system to become unusable
    df['value'] = df['value'].apply(lambda x: 0 if isinstance(x, str) else x)

    #Get all unique variable names in the data frame
    variable_names = df.entry.unique()
    print(df)
    
    
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
        print(slope)

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

