import sys
sys.path.append('/inc')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
from sklearn.linear_model import LinearRegression
import inc.encryption_functions as ef
from flask import render_template, request
import matplotlib.pyplot as plt
import seaborn as sns

def get_x_days_data(num_days):
# Connect to the SQLite database
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    sql_query = f"SELECT * FROM journal WHERE for_date >= '{(date.today()-timedelta(days=num_days)).isoformat()}'"
    # Get the data from the database using pandas
    df = pd.read_sql_query(sql_query, conn)
    df = ef.decrypt_df(df, ['entry','value','value_data_type'])
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
def create_graph(df):
    # drop wont be needed I jsut have tset data with dupes
    
    print(df)
    df = df.drop_duplicates()
    print(df)
    var_names_types = df.groupby(['for_date','entry','value_data_type'])
    df['date'] = pd.to_datetime(df['date_time_stamp']).dt.date

    df = df.pivot(index='for_date', columns='entry', values='value')
    #df = df.reset_index()

    # Get the list of variable names
    var_names = df.columns.tolist()
    
    if request.method == 'POST':
        # Get the selected variable from the form data
        selected_var = request.form['variable']
        print(var_names_types)
        if selected_var in var_names_types:
            if var_names_types[selected_var]['value_data_type'] == 'Integer':
                df[selected_var] = df[selected_var].fillna(0).astype(int)
            # Create a line plot using seaborn
            fig = plt.figure()
            sns.lineplot(x='for_date', y=selected_var, data=df)
            plt.xlabel('Date')
            plt.ylabel(selected_var)
            plt.title('Line Plot of {}'.format(selected_var))
            plt.tight_layout()
            plt.savefig('static/plot.png')
        else:
            print(f"column '{selected_var}' not found in data")
        
        # Render the HTML template with the plot image
        return var_names
    else:
        # Get the selected variable from the form data
        selected_var = 'Day Quality'
        df[selected_var] = df[selected_var].fillna(0).astype(int)
        # Create a line plot using seaborn
        fig = plt.figure()
        sns.lineplot(x='for_date', y=selected_var, data=df)
        plt.xlabel('Date')
        plt.ylabel(selected_var)
        plt.title('Line Plot of {}'.format(selected_var))
        plt.tight_layout()
        plt.savefig('static/plot.png')
    # If the request method is GET, render the HTML template with the form
        return var_names

get_trending_dictionary()