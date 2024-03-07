# -*- coding: utf-8 -*-
"""
Created on Thu Nov 30 22:19:50 2023

@author: torbe
"""


import datetime as dt
import numpy as np
from classes import DB, Vorhersagewert
from tensorflow.keras.models import load_model

def solarpower_regression(start_date, end_date):

    model_path = "./model_regression.h5"
    
    min_leist_train = 0
    max_leist_train = 64.752
    
    leist = [[min_leist_train, min_leist_train, max_leist_train],[min_leist_train, min_leist_train, max_leist_train]]
    
    # Import der Daten aus DB   
    data = DB.getGlobalstrahlungML(start=start_date, end=end_date)
    
    features = []
    
    for i in range(0,len(data)):
        # time_db = str(data[i][0])
        # date_object = datetime.strptime(time_db, "%Y-%m-%d %H:%M:%S")
        date_object = data[i][0]
        time_month = int(date_object.month)
        time_hour = int(date_object.hour)
        features.append([time_month, time_hour, data[i][1]])


    features = np.array(features)
    leist = np.array(leist)

    print(features)
    
    model = load_model(model_path)
    predictions = model.predict(features)
    
    data_send_db = []
    # Datenan DB senden
    for i in range(0,len(predictions)):
        if data[i][0] == 0 or data[i][1] == None or data[i][1] == 9999:
            data_send_db.append(Vorhersagewert(data[i][0], None, 0, None, None))
        else:     
            data_send_db.append(Vorhersagewert(data[i][0], None, round(float(predictions[i]), 4), None, None, None))
    DB.insertPrediction(data_send_db)
    
    return True




def main():
    start = dt.datetime.now()
    end = start + dt.timedelta(hours=12, minutes=0)
    solarpower_regression(start, end)


if __name__ == '__main__':
    main()
    

  
  
