import requests, json, time
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore


####追加したいチャネル名#####
key = 'tsukiyume_jp'
#########
firebase_secret = ''#firebaseの秘密鍵
project_id = ""#FirebaseおよびGCPのプロジェクトID
doc_name = ""#鍵を収めるドキュメント名
value = ''
def getStreams(client_id, Authorization, query):
    #ユーザidを取得する
    url = 'https://api.twitch.tv/helix/users?login='+ query
    headers = {'Client-ID': client_id,
           'Authorization': 'Bearer ' +Authorization}
    r = requests.get(url, headers=headers)
    row_data = r.json() 
    return row_data
def getToken(db):
    #FireStoreからOAuthトークンを取得する
    docRef = db.collection('users').document(doc_name)
    doc = docRef.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

cred = credentials.Certificate(firebase_secret) # ダウンロードした秘密鍵
firebase_admin.initialize_app(cred)
db = firestore.client()
keys = getToken(db)
data = getStreams(keys['client_id'], keys['OAuth'],key)['data']
value = data[0].get('id')
doc = db.collection('users').document('subscribe')
doc.update({
    key:value,
})
