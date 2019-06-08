import firebase_admin
import datetime
from enum import Enum
from firebase_admin import credentials
from firebase_admin import firestore
from Levenshtein import distance
from google.cloud.firestore_v1 import ArrayUnion, ArrayRemove

cred = credentials.Certificate('firestore_key.json')

# init firebase
firebase_admin.initialize_app(cred)

# init firestore
db = firestore.client()
user_ref = db.collection("users")
product_ref = db.collection("products")

def addProduct(user_id, product_id, product):
    """
    Args:
        user_id (str): The id link to the user's firestore document.
        product_id (str): The id link to the product's firestore ducument.
        product (dict): A dictionary which includes all data for the
            on-selling product.
    """
    try:
        # add a product
        ref = db.collection("products").document(str(product_id))
        ref.set(product)
        linkProductToUser(user_id, product_id, list_name="onsale_items")
    except Exception as e:
        raise e


def getProductBasicInfo(product):
    """
    Args:
        product (dict): All data of the products.
    Return:
        product_basic_info (dict): Return basic info we need, including
        these elements:
            {
                'id',
                'product_name',
                'images'
            }
    """

    if ('product_name' in product) and ('images' in product):
        product_basic_info = {
            'id': product['id'], 'product_name': product['product_name'], 'images': product['images']}
        return product_basic_info
    return None

# TODO getNProductBasicInfo(n)

def getAllProductBasicInfo():
    """
    Return:
        products_basic_info (dict): Basic info for all products.
    """
    products_basic_info = []
    collection_ref = db.collection('products')

    for doc in collection_ref.get():

        product = getProduct(doc.id)
        basic_info = getProductBasicInfo(product)
        if basic_info != None:
            products_basic_info.append(basic_info)

    return products_basic_info


def createProductDict():
    time_format = '%Y-%m-%d %H:%M'
    product = {
        'product_name': '',
        'id': '',
        'status': 0,
        'trading_type': 0,
        'description': '',
        'trading_method': '',
        'category': '',
        'seller': '',
        'price': 0,
        'current_price': 0,
        'price_per_mark': 0,
        'highest_buyer_id': '',
        'create_time': datetime.datetime.strptime(datetime.datetime.now().strftime(time_format), time_format),
        'deadline': datetime.datetime.strptime((datetime.datetime.now() + datetime.timedelta(days = 7)).strftime(time_format), time_format),
        'images': [],
        'qas': [],
    }
    return product


def createUserDict():
    user = {
        # 'account': '',
        # 'password': '',
        'idToken': '',
        'user_name': '',
        'email': '',
        'phone': '',
        'contact': '',
        'address': '',
        'tp_info': {
            'provider': '',
            'uid': '',
        },
        'tracking_items': [],
        'bidding_items': [],
        'done_items': [],
        'onsale_items': [],
        'dealing_items': [],
        'buyer_rate': 0,
        'seller_rate': 0,
    }
    return user


def getProduct(product_id):
    """
    Args:
        product_id (str): The id of the product.
    Returns:
        product (dict): All data of the products.
    """
    ref = db.collection("products").document(product_id)
    product = ref.get().to_dict()
    return product


def changeProductStatus(user_id, product_id, status):
    pass

def createNewUser(user_id, user_data):
    try:
        ref = db.collection('users').document(user_id)
        ref.set(user_data)
    except Exception as e:
        raise e


def getUserInfo(user_id):
    try:
        ref = db.collection('users').document(user_id)
        return ref.get().to_dict()
    except Exception as e:
        raise e


def updateUserInfo(user_id, user_data):
    try:
        ref = db.collection('users').document(user_id)
        ref.update(flattenDict(user_data))
    except Exception as e:
        raise e


def checkUserInfoCompleteness(user_id):
    try:
        ref = db.collection('users').document(user_id)
        data = ref.get().to_dict()
        if (data['user_name'] is not "") and \
            (data['phone'] is not "") and \
            (data['address'] is not "") and \
            (data['contact'] is not ""):
            return True
        else:
            return False
    except Exception as e:
        return False


# --- Developing --- #
# --- 2019/06/08 --- #
# Haven't Tested Yet #
def searchProducts(string, n):
    """
    Args: 
        string(str): Search string.
        n(int): Expect number of results.
    Return:
        result(list): Including **FULL** data from firestore. Ranked ascending.
    """
    result = []
    _max_distance = -1
    basicInfos = getAllProductBasicInfo()

    # This PROBABLY WORKS...
    # l => lowerbound, r => upperbound, range always => [l, r]
    def binary_search(dist, l, r):
        nonlocal result
        if l > r:
            return l
        if dist > result[(l+r)//2][0]:
            return binary_search(dist, (l+r)//2 + 1, r)
        elif dist < result[(l+r)//2][0]:
            return binary_search(dist, l, (l+r)//2 - 1)
        else:
            return (l+r)//2

    for data in basicInfos:
        if result:  # if result is not empty
            dist = distance(data['product_name'], string)
            # insert to the position of its edit distance
            position = binary_search(dist, 0, len(result)-1)
            # result already have n elements, if position
            if len(result) > n and position > _max_distance:
                continue
            result.insert((position, data))
            _max_distance = data[0] if data[0] > _max_distance else _max_distance

    return [element[1] for element in result][:n]


def linkProductToUser(user_id, product_id, list_name="onsale_items"):
    """
    Args:
        list_name (str): Decide which list @ firestore collection
            ``users`` should ``product_id`` store at, including these
            options:
                {
                    "onsale_items",
                    "tracking_items",
                    "bidding_items",
                    "dealing_items",
                    "done_items",
                }
        user_id (str): The id link to the user's firestore document.
        product_id (str): The id link to the product's firestore document.
    """

    # link the product to user(seller)
    try:
        ref = db.collection("users").document(user_id)
        ref.update({list_name: ArrayUnion([product_id])})
    except Exception as e:
        raise e


def unlinkProductFromUser(user_id, product_id, list_name="onsale_items"):
    try:
        ref = product_ref.document(str(product_id))
        ref.update({list_name: ArrayRemove([product_id])})
    except Exception as e:
        raise e


class ArrayOps(Enum):
    ADD = 1
    DELETE = 2


def flattenDict(d, mode=ArrayOps.ADD):
    ret = {}
    try:
        for key, value in d.items():
            if type(value) is not dict:
                if type(value) is list:
                    value = ArrayUnion(value) if mode == ArrayOps.ADD else ArrayRemove(value)
                ret.update({key: value})
            else:
                for key_, value_ in flattenDict(value).items():
                    ret.update({str(key)+'.'+str(key_): value_})
    except Exception as e:
        pass
    return ret

def updateProduct(product_id, product, mode=ArrayOps.ADD):
    """
    Args:
        user_id (str): The id link to the user's firestore document.
        product_id (str): The id link to the product's firestore ducument.
        product (dict): A dictionary which includes all data for the
            on-selling product.
    """
    try:
        ref = db.collection("products").document(str(product_id))
        ref.update(flattenDict(product, mode))
    except Exception as e:
        raise e

# TODO
def deleteProduct(product_id):
    try:
        product_ref.document(str(product_id)).delete()
    except Exception as e:
        raise e
# TODO
def transferProductStatus(user_id, product_id, status):
    try:
        ref = product_ref.document(product_id)
        # ref.update({'status': status})
    except Exception as e:
        raise e
# --- Developing --- #
