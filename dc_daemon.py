import netCDF4 as nc
import requests
import os
import datetime as dt
import time
import zipfile as zip
import numpy as np
import re
from classes import Realwert, DB, Vorhersagewert



def download_file(url):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename


def getStrompreis():
    try:
        resp = requests.get(url="https://api.awattar.de/v1/marketdata")
    except requests.exceptions.RequestException as e:
        print(e)
        return False

    if resp.status_code == 200:
        data = resp.json()['data']

        entries = []
        for el in data:
            starttime = dt.datetime.fromtimestamp(el['start_timestamp']/1000)
            price = el['marketprice']

            for i in range(12):
                timestamp = starttime+dt.timedelta(minutes=i*5)
                temp = Realwert(timestamp, None, None, None, price)
                entries.append(temp)

        DB.insertRealwerte(entries)
        return True
    else:
        return False

def getPVRealtime():
    try:
        resp = requests.get(url="http://141.41.235.28/JSON_PV_IPT/PV2020_231011.php")
    except requests.exceptions.RequestException as e:
        print(e)
        return False

    if resp.status_code == 200:
        response_json = resp.json()[0]
        stamp_minutes = int(response_json['Zeitstempel'][15:16])
        delta = stamp_minutes-5 if stamp_minutes > 5 else stamp_minutes
        timestamp = dt.datetime.strptime(response_json['Zeitstempel'][:-7], '%Y-%m-%d %H:%M') - dt.timedelta(minutes=delta)
        leistung = round(float(response_json['Strom_gesamt']) * 230 / 1000, 4)
        energie = round(leistung * 5/60, 4)

        entries = []

        last = DB.getRealwert(start=timestamp-dt.timedelta(minutes=6), end=timestamp-dt.timedelta(minutes=1))[0]
        if last.leistung == None:
            last.leistung = leistung
            last.energie = energie
            entries.append(last)

        entry = Realwert(timestamp, None, leistung, energie, None)
        entries.append(entry)
        DB.insertRealwerte(entries)
        return True

    return False

def getGlobalstrahlung():
    URL="https://opendata.dwd.de/weather/satellite/radiation/sis/"

    def get_file_name(url):
        res = requests.get(url=url).content.decode()
        file_name = ""
        ind=0
        while not "DE" in file_name:
            ind+=1
            indices = [m.start() for m in re.finditer('>SISin', res)]
            start = int(indices[len(indices)-ind]+1)
            end = int(start)+24
            file_name = res[start:end]
        return file_name

    file_name = get_file_name(url=URL)
    local_file = download_file(url=f'https://opendata.dwd.de/weather/satellite/radiation/sis/{file_name}')

    BS = (52.25, 10.5)

    ds = nc.Dataset(local_file)
    sis = ds.variables['SIS']
    time = ds.variables['time']
    lat, lon = ds.variables['lat'], ds.variables['lon']


    def get_closest_index(lats, lons, loc_lat, loc_lon) -> tuple[int, int]:
        # squared distance of every point on grid
        dist_sq = (lats-loc_lat)**2 + (lons-loc_lon)**2

        # 1D index of minimum dist_sq element
        index_min = dist_sq.argmin()

        #return 2D index for lat and lon vals
        return index_min

    latvals = lat[:]
    lonvals = lon[:]
    index_min = get_closest_index(latvals, lonvals, BS[0], BS[1])

    gs_now = sis[0, latvals[index_min], lonvals[index_min]].tolist()

    date = dt.datetime.strptime(str(dt.date.today()), "%Y-%m-%d") + dt.timedelta(seconds=time[:][0], hours=1)

    ds.close()
    os.remove(local_file)

    last_entry = DB.getRealwert(start=date-dt.timedelta(minutes=15), end=date-dt.timedelta(minutes=15))
    new_entries = []
    if len(last_entry) > 0:
        last_entry = last_entry[0]
        if last_entry.globalstrahlung == None:
            last_entry.globalstrahlung = 0

        delta = gs_now - last_entry.globalstrahlung

        for i in range(1, 3):
            gs = round(last_entry.globalstrahlung + 1/3*delta, 4)
            timestamp = date-dt.timedelta(minutes=15-5*i)
            new_entries.append(Realwert(timestamp, gs, None, None, None))

    new_entries.append(Realwert(date, gs_now, None, None, None))
    DB.insertRealwerte(new_entries)

    return True

def getGSForecast():
    # 4 Stunden delta weil +1 für Zeitzone, -11 Minuten weil neue Daten um XX:11 Uhr abgerufen werden, +3 weil Vorhersage bei drei Stunden in der Zukunft beginnt. Siehe https://www.dwd.de/DE/leistungen/fernerkund_globalstrahlung_sis/fernerkund_globalstrahlung_sis.html letztes Beispiel auf der Seite
    # Funktion gibt vorhersage in Fünfminutenschritten zurück, Wert bleibt aber für jede Stunde gleich

    current_utc_datetime= dt.datetime.now() - dt.timedelta(hours=1)

    current_minutes = int(current_utc_datetime.strftime("%M"))
    if current_minutes < 11:
        current_utc_datetime = current_utc_datetime - dt.timedelta(hours=1)

    forecast_url = f'https://opendata.dwd.de/weather/satellite/radiation/sis/SISfc{current_utc_datetime.strftime("%Y%m%d%H")}_fc%2B18h-DE.nc' # stimmt so nicht
    forecast_file_name = download_file(forecast_url)

    BS = (52.25, 10.5)

    ds = nc.Dataset(forecast_file_name)
    sis = ds.variables['SIS']
    time = ds.variables['time']
    lat, lon = ds.variables['lat'], ds.variables['lon']

    def get_closest_index(lats, lons, loc_lat, loc_lon) -> tuple[int, int]:
        # squared distance of every point on grid
        dist_sq = (lats-loc_lat)**2 + (lons-loc_lon)**2

        # 1D index of minimum dist_sq element
        index_min = dist_sq.argmin()

        #return 2D index for lat and lon vals
        return index_min

    timevals  = time[:]
    latvals = lat[:]
    lonvals = lon[:]
    index_min = get_closest_index(latvals, lonvals, BS[0], BS[1])
    bs_sis = [sis[i, latvals[index_min], lonvals[index_min]] for i in range(len(timevals))]
    ds.close()
    os.remove(forecast_file_name)

    gs_vals = []
    for i in range(len(timevals)):
        for j in range(12):
            t = timevals[i]+j/12
            date = dt.datetime.strptime(str(dt.date.today()), "%Y-%m-%d") + dt.timedelta(seconds=t*3600)
            gs_vals.append(Vorhersagewert(date, round(np.interp(t, timevals, bs_sis), 2), None, None, None, None))

    DB.insertPrediction(gs_vals)

    return True


def main():
    while True:
        start = time.time()
        getStrompreis()
        getPVRealtime()
        getGlobalstrahlung()
        getGSForecast()
        end = time.time()

        delta = end-start
        time.sleep(120-delta if delta<120 else 0)


if __name__ == '__main__':
    main()
