from flask import Flask, request, make_response
import pickle
import threading
import numpy as np
import sqlite3
from flask import g
import os

lock = threading.Lock()
client_weights = {}
max_client = 3
global_client = None
pairs = []

DATABASE = "database.db"


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


app = Flask(__name__)


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False, commit=False):
    with app.app_context():
        db = get_db()
        cur = db.execute(query, args)
        rv = cur.fetchall()
        if commit:
            db.commit()
        cur.close()

    return (rv[0] if rv else None) if one else rv


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource(os.path.join(os.path.dirname(__file__), 'schema.sql'), mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


init_db()


def combine_models_with_score():
    global client_weights, global_client, pairs

    global_client = client_weights[list(client_weights.keys())[0]]
    averageScore = 0

    pairs.append(list(client_weights.keys())[0])
    for key in list(client_weights.keys()):
        averageScore += client_weights[key]["score"]
    averageScore /= len(list(client_weights.keys()))

    for key in list(client_weights.keys())[1:]:
        global_client["weights"] = global_client["weights"] + \
            (client_weights[key]["weights"] *
             (np.float64(client_weights[key]["score"]) / averageScore))
        pairs.append(key)


def combine_average():
    global client_weights, global_client, pairs

    global_client = client_weights[list(client_weights.keys())[0]]

    for key in list(client_weights.keys()):
        pairs.append(key)

    for i in range(len(global_client["weights"])):
        for key in list(client_weights.keys())[1:]:
            global_client["weights"][i] = (
                global_client["weights"][i] + client_weights[key]["weights"][i])
        global_client["weights"][i] /= float(max_client)


# insert that later doesnot accept pre from rear
@app.route("/get_weights", methods=["POST"])
def get_model():

    data = pickle.loads(request.data)
    assert type(data) is dict

    query = "SELECT * from clients where name = ?"
    
    res = query_db(query, [data.get("proc_name")])
    print(res)
    if res is not None:
        if type(res) is list:
            if len(res) != 0:
                query = """DELETE FROM clients WHERE id = ?"""

                for r in res:
                    query_db(query, [r[0]], commit=True)
    
    query = """INSERT INTO clients(name, weights, score) 
            values (?, ?, ?)"""

    res = query_db(query, [data["proc_name"], sqlite3.Binary(
        pickle.dumps(data["weights"])), data["score"]], commit=True)
            

    clients = query_db("SELECT * from clients ORDER BY id ASC")
    for client in clients:
        print("client id -> ", client[1])

    if len(clients) >= max_client:
        major_client = pickle.loads(clients[0][2])

        for i in range(len(major_client)):
            for client in clients[1:max_client]:
                major_client[i] = major_client[i] + pickle.loads(client[2])[i]

            major_client[i] = major_client[i] / float(max_client)

        
        # for client in clients[:max_client]:
        #     query_db("DELETE FROM clients WHERE id = ?",
        #              args=(client[0],), commit=True)

        query_db(
            """INSERT INTO global_model(client_1_name, client_2_name, client_3_name, model, client_count) VALUES(?, ?, ?, ?, ?) """,
            args=(clients[0][1], clients[1][1], clients[2][1],
                  pickle.dumps(major_client), 0.0),
            commit=True
        )
        query_db("DELETE FROM clients", commit=True)
        
        print("major model created.")
        return make_response({"message": "second model inserted"}, 200)

    return make_response({"message": "weights recieved without any problems"}, 200)


@app.route("/get_glob_model", methods=["GET"])
def get_global_model():

    proc_name = str(request.args.get("proc_name", "")).strip()

    with lock:
        res = query_db(
            """SELECT * FROM global_model WHERE client_1_name = ? OR client_2_name = ? OR client_3_name = ?""",
            args=(proc_name, proc_name, proc_name)
        )

        if len(res) != 0:
            res = res[0]
            print(res[1], res[2])
            if res[5] == 2:
                query_db("DELETE FROM global_model", commit=True)
            elif res[5] == 0:
                print(res[5])
                
                query_db("UPDATE global_model SET client_count = ? WHERE id = ?", args=(
                    res[5]+1, res[0]), commit=True)

            return pickle.dumps({
                "weights": pickle.loads(res[4])
            }), 200

    return make_response({"message": "clients are not sufficed 1"}, 400)


@app.route("/index", methods=["GET"])
def index():
    return "<h1> HELLO </h1>"


@app.route("/reset", methods=["POST"])
def reset():
    query_db("DELETE FROM global_model", commit=True)
    query_db("DELETE FROM clients", commit=True)
    return make_response({"message": "done"}, 200)


@app.route("/reset1", methods=["POST"])
def reset1():
    query_db("DELETE FROM global_model", commit=True)
    query_db("DELETE FROM clients", commit=True)
    return make_response({"message": "done"}, 200)
