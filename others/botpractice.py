import requests, json, time
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
doc_name = ""#鍵を収めるドキュメント名
firebase_secret = ''#firebaseの秘密鍵
discord_webhook = ""
triggerURL = ''#backendのwebhookURL

##########
def getOAuthKey(client_id, client_secret):
    OAuthUrl = 'https://id.twitch.tv/oauth2/token'
    form =  {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    r = requests.post(OAuthUrl, params=form)
    row_data = r.json()
    Authorization = 'Bearer ' + row_data['access_token']
    return Authorization

def getStreams(client_id, Authorization, query):
    url = 'https://api.twitch.tv/helix/streams?'+ query
    headers = {'Client-ID': client_id,
           'Authorization': Authorization}
    r = requests.get(url, headers=headers)
    row_data = r.json()
    return row_data

def makeQueryOR(elements,insert_word):
    query = ''
    for index, item in enumerate(elements):
        if index==0:
            query = insert_word + item
        else:
            query = query + '&' + insert_word + item
    return query
def sendDiscord(jsonfl):
    webhookURL = discord_webhook 
    url = 'https://www.twitch.tv'
    user_image = jsonfl['thumbnail_url']
    width = '160'
    height = '90'
    user_image = user_image.replace('{width}',width).replace('{height}',height)
    headers = {'Content-Type': 'application/json'}
    embeds = [{
        'title': jsonfl['title'],
        'description':jsonfl['user_name'],
        'color': int('C030C0', 16),
        'url': url+'/'+jsonfl['user_login'],
        'timestamp': jsonfl['started_at'],
        'image':{
            'url': user_image
        }
    }]
    mainContent = {
        'embeds': embeds
    }
    response = requests.post(webhookURL,json.dumps(mainContent),headers=headers)
    print(response)
########
#Step0 鍵を取得する
cred = credentials.Certificate(firebase_secret) # ダウンロードした秘密鍵
firebase_admin.initialize_app(cred)
db = firestore.client()
doc = db.collection('users').document(doc_name).get()
dict = doc.to_dict()
client_id = dict['client_id']#クライアント_id
client_secret = dict['client_secret']#秘密鍵(OAuthでアプリアクセストークンを取得するのに使う)

#Step1 Authorizationを取得する
Authorization = getOAuthKey(client_id,client_secret)

#Step2: DBからユーザ名を取得してクエリを作成する
users = ["mogra","sabaco_waseda"]
query = makeQueryOR(users,'user_login=')

#Step3: 配信情報を取得する
r = getStreams(client_id,Authorization,query)
#print(r)

#Step4 クエリのレスポンスをdoscordに送る
UNIXTIME = int(time.time())
JST = timezone(timedelta(hours=+9), 'JST')
nowtimeJST = datetime.fromtimestamp(UNIXTIME,JST)
limited = 60*60*3 #15分おきにプログラムを回す
for index,item in enumerate(r['data']):
    print(item)
    USTstreamTime = datetime.strptime(item['started_at'].replace('Z','+00:00'),'%Y-%m-%dT%H:%M:%S%z')#string->datetime
    JSTstreamTime = USTstreamTime.astimezone(JST)
    print(nowtimeJST)
    print(JSTstreamTime)
    UNIXstreamTime = USTstreamTime.timestamp()
    diff = UNIXTIME - UNIXstreamTime
    print(diff)
    if diff<=limited:
        sendDiscord(item)