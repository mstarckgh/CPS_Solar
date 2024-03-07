"""
author: Matthias Starck
file:   classes.py
desc:   Klassen für den vereinfachten Zugriff auf die Datenbank.
"""


import datetime


class Realwert():
    def __init__(self, timestamp:datetime.datetime, globalstrahlung, leistung, energie, strompreis, id=None) -> None:
        self.timestamp = timestamp
        self.globalstrahlung = globalstrahlung
        self.leistung = leistung
        self.energie = energie
        self.strompreis = strompreis


class Vorhersagewert:
    def __init__(self, timestamp:datetime.datetime, globalstrahlung, leistung, zukaufleistung, laden, pi, id=None) -> None:
        self.timestamp = timestamp
        self.globalstrahlung = globalstrahlung
        self.leistung = leistung
        self.zukaufleistung = zukaufleistung
        self.laden = laden
        self.pi = pi


class DB:
    def connect():
        import mysql.connector
        cnx = mysql.connector.connect(user='main_user', password='ComCom2023!',
                                    host='ec2-3-125-3-235.eu-central-1.compute.amazonaws.com', port=3306,
                                    database='ComCom')
        return cnx

    def RealwertFromList(all_attributes:list) -> Realwert:
        res = all_attributes
        return Realwert(timestamp=res[0], globalstrahlung=res[1], leistung=res[2], energie=res[3], strompreis=res[4])

    def VorhersagewertFromList(all_attributes:list) -> Vorhersagewert:
        res = all_attributes
        return Vorhersagewert(timestamp=res[0], globalstrahlung=res[1], leistung=res[2], zukaufleistung=res[3], laden=res[4], pi=res[5])

    def insertRealwerte(entries:list[Realwert]):
        QUERRY = """
INSERT INTO realwerte
(timestamp, globalstrahlung, leistung, energie, strompreis)
VALUES
(%s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
"""
        temp = entries[0]
        for key in temp.__dict__.keys():
            if temp.__dict__[key] is not None:
                QUERRY = QUERRY + f"{key} = VALUES({key}),\n"
        QUERRY = QUERRY[:-2] + ";"

        print(QUERRY)

        with DB.connect() as con:
            c = con.cursor()
            c.executemany(QUERRY, [[el.timestamp, el.globalstrahlung, el.leistung, el.energie, el.strompreis] for el in entries])
            con.commit()

    def insertPrediction(entries:list[Vorhersagewert]):
        QUERRY = """
INSERT INTO vorhersagewerte
(timestamp, globalstrahlung, leistung, zukaufleistung, laden, pi)
VALUES
(%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
"""
        temp = entries[0]
        for key in temp.__dict__.keys():
            if temp.__dict__[key] is not None:
                QUERRY = QUERRY + f"{key} = VALUES({key}),\n"
        QUERRY = QUERRY[:-2] + ";"

        print(QUERRY)

        with DB.connect() as con:
            c = con.cursor()
            c.executemany(QUERRY, [[el.timestamp, el.globalstrahlung, el.leistung, el.zukaufleistung, el.laden, el.pi] for el in entries])
            con.commit()

    def getRealwert(order_by:str = "timestamp", ascending:bool = True, **kwargs) -> list[Realwert]:
        QUERRY = "SELECT * FROM realwerte"
        if len(kwargs)>0:
            QUERRY = QUERRY + ' WHERE'
            if 'start' in kwargs:
                QUERRY = QUERRY + f" timestamp >= '{kwargs['start']}' AND"
                kwargs.pop('start')
            if 'end' in kwargs:
                QUERRY = QUERRY + f" timestamp <= '{kwargs['end']}' AND"
                kwargs.pop('end')
            for arg in kwargs:
                if type(kwargs[arg])==str:
                    if '%' in kwargs[arg] or '_' in kwargs[arg]:
                        QUERRY = QUERRY + f" {arg} LIKE '{kwargs[arg]}' AND"
                    else:
                        QUERRY = QUERRY + f" {arg}='{kwargs[arg]}' AND"
                else:
                    QUERRY = QUERRY + f" {arg}={kwargs[arg]} AND"
            QUERRY = QUERRY[:-4]
        QUERRY = QUERRY + f" ORDER BY {order_by} {'ASC' if ascending else 'DESC'};"

        with DB.connect() as con:
            c = con.cursor()
            c.execute(QUERRY)
            res = c.fetchall()

        entries = []
        for entry in res:
            entries.append(DB.RealwertFromList(entry))
        return entries

    def getVorhersagewert(order_by:str = "timestamp", ascending:bool = True, **kwargs) -> list[Vorhersagewert]:
        QUERRY = "SELECT * FROM vorhersagewerte"
        if len(kwargs)>0:
            QUERRY = QUERRY + ' WHERE'
            if 'start' in kwargs:
                QUERRY = QUERRY + f" timestamp >= '{kwargs['start']}' AND"
                kwargs.pop('start')
            if 'end' in kwargs:
                QUERRY = QUERRY + f" timestamp <= '{kwargs['end']}' AND"
                kwargs.pop('end')
            for arg in kwargs:
                if type(kwargs[arg])==str:
                    if '%' in kwargs[arg] or '_' in kwargs[arg]:
                        QUERRY = QUERRY + f" {arg} LIKE '{kwargs[arg]}' AND"
                    else:
                        QUERRY = QUERRY + f" {arg}='{kwargs[arg]}' AND"
                else:
                    QUERRY = QUERRY + f" {arg}={kwargs[arg]} AND"
            QUERRY = QUERRY[:-4]
        QUERRY = QUERRY + f" ORDER BY {order_by} {'ASC' if ascending else 'DESC'};"


        with DB.connect() as con:
            c = con.cursor()
            c.execute(QUERRY)
            res = c.fetchall()

        entries = []
        for entry in res:
            entries.append(DB.VorhersagewertFromList(entry))
        return entries

    def getGlobalstrahlungML(start=datetime.datetime, end=datetime.datetime):
        QUERRY = f"SELECT timestamp, globalstrahlung FROM vorhersagewerte WHERE timestamp>='{start}' AND timestamp<='{end}' ORDER BY timestamp ASC;"
        with DB.connect() as con:
            c = con.cursor()
            c.execute(QUERRY)
            res = c.fetchall()
        return res

    def getDataForOpt(start, end):
        with DB.connect() as con:
            c = con.cursor()
            c.execute(f"""
                SELECT timestamp, strompreis
                FROM realwerte
                WHERE timestamp>='{start}'
                AND timestamp<='{end}'
            """)
            strom = c.fetchall()

        with DB.connect() as con:
            c = con.cursor()
            c.execute(f"""
                SELECT timestamp, leistung
                FROM vorhersagewerte
                WHERE timestamp>='{start}'
                AND timestamp<='{end}'
            """)
            leistung = c.fetchall()

        vorh_lesitung = []
        strompreis = []

        for el in strom:
            strompreis.append(el[1])

        for el in leistung:
            vorh_lesitung.append(el[1])

        return strompreis, vorh_lesitung

def main():
    pass



if __name__ == '__main__':
    main()
