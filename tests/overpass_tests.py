"""
premier jet de fichier test pour verifier que overpass fonctionne

autheur(s) : marc-emile scholer
date de creation : 10-05-26
"""
# va resolve avec pytest
import time
import pytest
from data.structures_communes import BBox
import data.OverPass.client_overpass as client
import data.OverPass.queries_overpass as q

# sleep entre chaque call api
@pytest.fixture(autouse=True)
def _rate_limit():
    yield
    time.sleep(2)

# Node ID OSM sommet du mont orford
_MONT_ORFORD_ID = 453949165

# aeroport de sherbrooke + riviere eaton
_BOX1 = BBox(45.45,-71.72,45.46,-71.62)
_WAY_IN_BOX1 = 1124055322


#tester get 1 node
def test_get_node_by_id():
    query = q.query_node_by_id(_MONT_ORFORD_ID)
    res = client.get_data(query, verbosity ="geom")

    assert res is not None
    
    print(f"{res}")

def test_get_way_by_id():
    query = q.query_way_by_id(_WAY_IN_BOX1)
    res = client.get_data(query, verbosity = "geom")

    assert res is not None
    
    print(f"{res}")

#tester get 1 bounding box 
def test_get_box():
    query = q.query_box(_BOX1)
    res = client.get_data(query,verbosity = "geom")

    assert res is not None

    print(f"{res}")

#tester une query dans une box
def test_query_in_box():
    query = q.query_way_by_id(_WAY_IN_BOX1)

    res = client.get_data(query, verbosity = "geom")

    res_1 = client.get_data(query,_BOX1, verbosity = "geom")

    assert res is not None

    assert res == res_1
    
    print(f"{res}")

def test_print_box(bbox):
    print(f"{bbox}")
    






