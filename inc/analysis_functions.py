import sys
sys.path.append('/inc')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from sklearn.linear_model import LinearRegression
import inc.encryption_functions as ef

def get_trending_dictionary():
    #dict to store our results
    result_dict = {}   
        
    # Connect to the SQLite database
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    
    # Define the SQL query to select all columns from the table
    sql_query = f"SELECT * FROM journal WHERE for_date >= '{(date.today()-timedelta(days=14)).isoformat()}'"


    # Get the data from the database using pandas
    df = pd.read_sql_query(sql_query, conn)
    df = ef.decrypt_df(df, ['entry','value','value_data_type'])
    #df['date'] = pd.to_datetime(df['date_time_stamp']).dt.date 
    #df['date_time_stamp'] = pd.to_datetime(df['date_time_stamp'])

 
    #Make sure all values are in an Integer or Binary format
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

get_trending_dictionary()