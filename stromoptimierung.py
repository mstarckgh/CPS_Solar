#!/usr/bin/env python
# coding: utf-8
# Author: Lieven Dümke

from pyomo.environ import *
import pyomo.environ as pyo
import datetime
import math
import numpy as np
from classes import DB, Vorhersagewert


def optimierung(start, end, menge):
    strompreis, solarleistung = DB.getDataForOpt(start, end)
    strompreis = [el if el is not None else 65 for el in strompreis]
    solarleistung = [el if el is not None else 0 for el in solarleistung]

    start_time = start
    end_time = end


    zeitunterschied = end_time - start_time

    zeit = math.floor(zeitunterschied.total_seconds() / (5 * 60))

    time_values = []

    current_time = DB.getVorhersagewert(start=start , end=start+datetime.timedelta(minutes=5), ascending=True)[0].timestamp
    print(current_time)
    while current_time <= end_time:
        time_values.append(current_time.strftime('%Y-%m-%d %H:%M:%S'))
        current_time += datetime.timedelta(minutes=5)

    zeitbereich = [i for i in range(zeit)]

    dict_zeit_zeitdaten = dict(zip(zeitbereich, time_values))

    EE = menge  # Alles in kW
    EML = 4.1
    ZML = 22
    G = 0.0
    for i in range(len(solarleistung)):
        if solarleistung[i] > ZML:
            solarleistung[i] = ZML

    K = dict(zip(zeitbereich, strompreis))
    P = dict(zip(zeitbereich, solarleistung))

    if zeit * ZML/12 < EE:
        EE = zeit * ZML/12

    model = ConcreteModel()

    step_x = [0.0, 1e-3, ZML]
    step_y = [0.0, 1.0, 1.0]

    oder_x = [0.0, 1.0, 2.0]
    oder_y = [0.0, 1.0, 1.0]

    model.p = Var(zeitbereich, within=Binary)
    model.z = Var(zeitbereich, within=Binary)
    model.L = Var(zeitbereich, within=NonNegativeReals, bounds=(0, ZML))
    model.h = Var(zeitbereich, within=Binary)
    model.h2 = Var(zeitbereich, within=Integers, bounds=(0, 2))


    expr1 = sum(model.L[i] * K[i] for i in zeitbereich)
    expr2 = sum((1 - model.p[i]) * P[i] * G for i in zeitbereich)
    model.obj = Objective(expr = expr1 - expr2, sense=minimize)

    for i in zeitbereich:
        if i not in zeitbereich:
            model.add_component("LadenNichtMöglich{0}".format(i),
                            Constraint(expr = model.p[i] + model.L[i] == 0))
        else:
            model.add_component("obere_leistungsgrenze{0}".format(i),
                           Constraint(expr = model.p[i] * P[i] + model.L[i] <= ZML))
            model.add_component("untere_leistungsgrenze{0}".format(i),
                           Constraint(expr=P[i] + model.L[i] >= EML * model.z[i]))
            model.add_component("unit_step{0}".format(i),
                            Piecewise(
                                model.h[i],
                                model.L[i],
                                pw_pts=step_x,
                                pw_constr_type='LB',
                                f_rule=step_y,
                                pw_repn='INC',
                            ))
            model.add_component("oder_bedingung{0}".format(i),
                               Constraint(expr = model.h2[i] == model.h[i] + model.p[i]))

            model.add_component("oder{0}".format(i),
                            Piecewise(
                                model.z[i],
                                model.h2[i],
                                pw_pts=oder_x,
                                pw_constr_type='EQ',
                                f_rule=oder_y,
                                pw_repn='INC',
                            ))
    model.constraint_EM = Constraint(expr=sum(model.p[i] * P[i] / 12 + model.L[i]/12 for i in zeitbereich) >= EE)

    opt = SolverFactory('glpk')
    opt_success = opt.solve(model)
    # model.display()

    dict_p_aktiv = {}
    dict_L_aktiv = {}
    dict_z_aktiv = {}
    for i in zeitbereich:
        dict_p_aktiv[dict_zeit_zeitdaten[i]] = model.p[i].value
        dict_L_aktiv[dict_zeit_zeitdaten[i]] = model.L[i].value
        dict_z_aktiv[dict_zeit_zeitdaten[i]] = model.z[i].value

    data_list = []
    for i in range(len(zeitbereich)):
        data_list.append(Vorhersagewert(time_values[i], None, None, model.L[i].value, model.z[i].value, model.p[i].value))



    DB.insertPrediction(data_list)


def main():
    start = datetime.datetime.strptime("2024-03-04 21:00", "%Y-%m-%d %H:%M")
    end = datetime.datetime.strptime("2024-03-04 21:45", "%Y-%m-%d %H:%M")

    optimierung(start, end, 25)


if __name__ == '__main__':
    main()
