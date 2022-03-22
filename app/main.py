from flask import Flask, request, make_response
import pickle
import threading
import numpy as np

lock = threading.Lock()
client_weights = {}
max_client = 2
global_client = None
pairs = []

app = Flask(__name__)


def combine_models_with_score():
    global client_weights, global_client

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
    global client_weights, global_client

    global_client = client_weights[list(client_weights.keys())[0]]

    for key in list(client_weights.keys())[:max_client]:
        pairs.append(key)

    for i in range(len(client_weights[key]["weights"])):
        for key in list(client_weights.keys())[1:]:
            global_client["weights"][i] = (
                global_client["weights"][i] + client_weights[key]["weights"][i])
        global_client["weights"][i] /= float(max_client)


@app.route("/get_weights", methods=["POST"])
def get_model():
    global client_weights
    data = pickle.loads(request.data)
    assert type(data) is dict

    for key in ["weights", "proc_name", "score"]:
        if key not in data.keys():
            return make_response({"message": f"{key} are not provided"}, 400)

    with lock:
        client_weights[data["proc_name"]] = {
            "weights": data["weights"],
            "score": data["score"]
        }
        try:
            if len(client_weights.keys()) == max_client:
                combine_average()
                client_weights = {}
        except Exception as ex:
            print("ex -> ", ex)

    return make_response({"message": "weights recieved without any problems"}, 200)


@app.route("/get_glob_model", methods=["GET"])
def get_global_model():
    global client_weights, global_client
    proc_name = str(request.args.get("proc_name", "")).strip()
    g_weight = None
    
    with lock:
        included = False
        for pair in pairs:
            if str(pair) == proc_name:
                included = True
        if not included:
            return make_response({"message": "clients are not sufficed 1"}, 400)
        pairs.remove(proc_name)
        g_weight = global_client["weights"]

    if g_weight is None:
        return make_response({"message": "clients are not sufficed 2"}, 400)
    c
    return pickle.dumps({
        "weights": g_weight
    }), 200


@app.route("/index", methods=["GET"])
def index():
    return "<h1> HELLO </h1>"
