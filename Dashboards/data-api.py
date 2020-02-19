#---------------------------------------
# Dashboard Data Server
# Version 1.0
#---------------------------------------

from flask import Flask, Response, render_template, request, redirect
from flask_cors import CORS
import requests as http
import json, pygal

app = Flask(__name__)
CORS(app)

def responsify(status,message,data={}):
    code = int(status)
    a_dict = {"data":data,"message":message,"code":code}
    try:
        return Response(json.dumps(a_dict), status=code, mimetype='application/json')
    except:
        return Response(str(a_dict), status=code, mimetype='application/json')

def get_chart(type, title, x_labels, chart_data):
    type = type.lower()
    if type == "bar":
        chart = pygal.Bar()
    elif type == "pie":
        chart = pygal.Pie()
    else:
        chart = pygal.Line()
    chart.title = title
    chart.x_labels = x_labels
    for series in chart_data:
        if type == "pie":
            chart.add(series, chart_data[series][0])
        else:
            chart.add(series, chart_data[series])
    return chart.render_data_uri()

def isNumeric(x):
    try:
        return float(x)
    except:
        return False

def JSONArray2HTMLtable(array):
    headers = array[-1].keys()
    inner_table = []
    for element in array:
        row = "<tr>%s</tr>" % "".join(["<td>%s</td>" % element[header] for header in headers])
        inner_table.append(row)
    return "<table>" + "<tr>%s</tr>" % "".join(["<th>%s</th>" % header for header in headers]) + "".join(inner_table) + "</table>"

def normalize(x):
    if isNumeric(x):
        return float(x)
    else:
        return str(x)

def localSearch(array, params, mode="AND"):
    try:
        def is_match(x):
            satisfied = 0
            for param in params:
                if param in x:
                    if isNumeric(x[param]):
                        if params[param][0] <= x[param] <= params[param][1]:
                            satisfied+=1
                    else:
                        if [y for y in params[param] if y.lower() == x[param].lower()]:
                            satisfied+=1
            if mode == "OR":
                return satisfied > 0
            else:
                return satisfied == len(params.keys())
        if params:
            return [x for x in array if is_match(x)]
        else:
            return array
    except:
        return array

@app.route("/data-filter")
def filter():
    global args
    args = dict(request.args)
    args = {key.lower():args[key][0] for key in args}
    def inline_tx(target):
        intermediate = map(normalize, get_var(target).split(","))
        if len(intermediate) == 1:
            if isNumeric(intermediate[0]):
                intermediate.insert(0,0)
        return intermediate
    def get_var(var):
        try:
            return args[var.lower()]
        except:
            return None
    unit = get_var("unit")
    title = get_var("title")
    table = get_var("table")
    data = http.post("https://ods4.herokuapp.com/ods/fetch_records", json.dumps({
        "tablename":"sample_dashboard",
        "constraints":{
            "unit":unit,
            "title":title
        },
        "strict":True,
        "restrict":["dashboard_data"],
        "operator":"AND"
    }), headers={"Content-Type":"application/json"}).json()["data"]
    if data:
        if unit == "settlements" and title == "Monthly Payment Analysis" and table == "FX TRANSACTIONS":
            try:
                params, mode = {"FX":inline_tx("FX")}, "AND"
            except:
                params, mode = {}, "OR"
        try:
            results = localSearch(data[0]["dashboard_data"][table], params, mode)
            code, msg, data = 200, "OK", {"chart":get_chart(get_var("chartType"), table, inline_tx("FX"), {param:[x[param] for x in results] for param in ["COUNT", "VALUE"]}), "table":JSONArray2HTMLtable(results)}
        except:
            code, msg, data = 400, "Error", {}
    else:
        code, msg, data = 400, "Error", {} 
    return responsify(code, msg, data)

# serve files
@app.route("/files/<path:filename>")
def get_file(filename):
    try:
        return app.send_static_file(filename)
    except:
        return "<h1> Error Serving File: %s <h1>" % filename



if __name__ == "__main__":
    app.run(threaded=True)