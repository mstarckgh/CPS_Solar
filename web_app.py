"""
author: Matthias Starck
file:   web_app.py
desc:   Flask back-end für CPS user interface.
"""

from flask import Flask, render_template, redirect, request, url_for
import datetime as dt
from classes import DB, Realwert, Vorhersagewert
import json
from solar_regression_runtime import solarpower_regression
from stromoptimierung import optimierung

app = Flask(__name__)

@app.route("/")
def index():
    last_entry = DB.getRealwert(start=dt.datetime.now()-dt.timedelta(minutes=15, hours=-1), end=dt.datetime.now()-dt.timedelta(minutes=10, hours=-1))[0]
    last_entry.leistung = round(last_entry.leistung, 4) if last_entry.leistung is not None else "Fehler"
    last_entry.strompreis = round(last_entry.strompreis/10, 2) if last_entry.strompreis is not None else "Fehler"

    if  last_entry.globalstrahlung is None:
        with DB.connect() as con:
            c = con.cursor()
            c.execute("SELECT * FROM realwerte WHERE globalstrahlung IS NOT NULL ORDER BY timestamp DESC")
            res = c.fetchone()
        last_entry.globalstrahlung = res[1]

    last_entry.globalstrahlung = round(last_entry.globalstrahlung, 2)


    charge = DB.getVorhersagewert(start=dt.datetime.now()-dt.timedelta(hours=-1, minutes=5), end=dt.datetime.now()+dt.timedelta(hours=1, minutes=5))
    if len(charge) < 1:
        charge = Vorhersagewert(dt.datetime.now(), None, None, None, False, None)
    else:
        charge = charge[0]

    return render_template("index.html", real=last_entry, pred=charge)


@app.route("/start_calc", methods=['GET', 'POST'])
def startCalc():
    if request.method == "POST":
        startDate = dt.datetime.strptime(request.form.get('startDate').replace('T', '-'), '%Y-%m-%d-%H:%M')
        endDate = dt.datetime.strptime(request.form.get('endDate').replace('T', '-'), '%Y-%m-%d-%H:%M')
        batteryCapacity = float(request.form.get('batteryCapacity'))

    if startDate < endDate:
        solarpower_regression(startDate, endDate)
        optimierung(startDate, endDate, batteryCapacity)
        return redirect("/", code=302)
    else:
        print("ERROR: startDate > endDate")
        return redirect("/", code=404)


@app.route("/data")
def data():
    if len(request.args) > 1:
        start = dt.datetime.strptime(request.args['start'], "%Y-%m-%d-%H:%M")
        end = dt.datetime.strptime(request.args['end'], "%Y-%m-%d-%H:%M")
    else:
        start = dt.datetime.now() - dt.timedelta(days=1, hours=-1)
        end = dt.datetime.now() + dt.timedelta(hours=1, minutes=-5)

    real = DB.getRealwert(start=start, end=end)
    prog = DB.getVorhersagewert(start=start, end=end)
    power = [el.leistung if el.leistung is not None else 0 for el in real]
    globalstrahlung = [el.globalstrahlung if el.globalstrahlung is not None else 0 for el in real]
    gs_prog= [el.globalstrahlung if el.globalstrahlung is not None else 0 for el in prog]
    strompreis = [el.strompreis if el.strompreis is not None else 0 for el in real]
    labels = [el.timestamp.strftime("%d.%m.%Y %H:%M") for el in real]

    return render_template("plots.html", labels=labels, globalstrahlung=globalstrahlung, gs_prog=gs_prog, power=power, strompreis=strompreis)

@app.route("/update_graph", methods=['GET', 'POST'])
def updateGraph():
    if request.method == "POST":
        startDate = request.form.get('startDate').replace('T', '-')
        endDate = request.form.get('endDate').replace('T', '-')

    return redirect(url_for("data", start=startDate, end=endDate))


if __name__ == '__main__':
    app.run()
