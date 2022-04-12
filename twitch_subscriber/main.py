import requests, json
import firebase_admin
from firebase_admin import credentials, firestore

project_id = ""#FirebaseおよびGCPのプロジェクトID
doc_name = ""#鍵を収めるドキュメント名
triggerURL = ''#backendのwebhookURL

def initializeFirestoreGCP():
    #GCPで使うfirestoreクライアントの初期化
    cred = credentials.ApplicationDefault()
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred,{
            "project_id": project_id,
        })
    db = firestore.client()
    return db

def getToken(db):
    #FireStoreからOAuthトークンを取得する
    docRef = db.collection('users').document(doc_name)
    doc = docRef.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

def generateToken(client_id, client_secret):
    #OAuthトークンを生成する
    OAuthUrl = 'https://id.twitch.tv/oauth2/token'
    form =  {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    r = requests.post(OAuthUrl, params=form)
    row_data = r.json()
    token = row_data['access_token']
    return token

def isValidToken(token):
    #OAuthトークンが有効かどうかを返す
    if token == None or not str:
        return False
    headers = {
        'Authorization':'Bearer ' + token
    }
    r = requests.get("https://id.twitch.tv/oauth2/validate", headers = headers)
    if r.ok:
        return True
    return False

def storeToken(token,db):
    #OAuthトークンをDBに保存する
    doc_ref = db.collection('users').document(doc_name)
    doc_ref.update({
    'OAuth':token,
    })

def getSubIds(keys):
    headers = {
        'CLIENT-ID': keys['client_id'],
        'Authorization': 'Bearer ' + keys['OAuth']
    }
    r = requests.get("https://api.twitch.tv/helix/eventsub/subscriptions", headers=headers)
    row_data = r.json()
    print(row_data)
    return row_data

def revokeSub(keys,IDs):
    #サブスクリプションを破棄する
    headers = {
        'CLIENT-ID': keys['client_id'],
        'Authorization': 'Bearer ' + keys['OAuth'],
        'content-type': 'application/json'
    }
    for item in IDs:
        params = {
            'id': item
        }
        requests.delete("https://api.twitch.tv/helix/eventsub/subscriptions", headers=headers,params=params)
    

def requestSub(keys,channels,callbackURL):
    headers = {
        'CLIENT-ID': keys['client_id'],
        'Authorization': 'Bearer ' + keys['OAuth'],
        'content-type': 'application/json'
    }
    body = {
        'type': 'stream.online',
        'version': '1', 
        'transport':{
            'method':'webhook',
            'callback': callbackURL,
            'secret': keys['sub_secret']
        }
    }
    condition = {}
    for item in channels:
        condition['BROADCASTER_USER_ID'] = item
        body['condition'] = condition
        #print(body)
        r = requests.post("https://api.twitch.tv/helix/eventsub/subscriptions", headers=headers,data=json.dumps(body))
        print(r.text)

def getStreams(client_id, Authorization, query):
    #ユーザidを取得する
    url = 'https://api.twitch.tv/helix/users?login='+ query
    headers = {'Client-ID': client_id,
           'Authorization': 'Bearer ' +Authorization}
    r = requests.get(url, headers=headers)
    row_data = r.json() 
    print(row_data)
    return row_data

def makeUserArray(db):
    arr = []
    doc = db.collection('users').document('subscribe').get().to_dict()
    for v in doc.values():
        arr.append(v)
    return arr
def buildStreamIDArr(row_data):
    arr = []
    data = row_data.get('data')
    #print(data)
    for item in data:
        id = item.get('id')
        arr.append(id)
    return arr
##########################

def main(event,context):
    db = initializeFirestoreGCP()
    keys = getToken(db)#FireStoreから鍵を受け取る
    if keys is None:
      print("ウンコ")
      return 0
    if isValidToken(keys.get('OAuth')) == False:#Oauthトークンの有効性を確認する
        print('If keyVaildation is false')#falseの場合に実行
        authKey = generateToken(keys['client_id'], keys['client_secret'])
        storeToken(authKey,db)
    data = getSubIds(keys)#現在のリクエストを取得する
    IDs = buildStreamIDArr(data)
    revokeSub(keys,IDs)#以前のリクエストを全て消す
    arr = makeUserArray(db)
    requestSub(keys,arr,triggerURL)#サブスクリクエストを生成
  