import requests, json
from flask import Flask,Response,request
import firebase_admin
from firebase_admin import credentials, firestore
import hmac
import hashlib

app = Flask(__name__)

project_id = ""#FirebaseおよびGCPのプロジェクトID
doc_name = ""#鍵を収めるドキュメント名
firebase_secret = ''#firebaseの秘密鍵
discord_webhook = ""
def initializeFirestore():
    #firestoreクライアントの初期化
    cred = credentials.Certificate(firebase_secret) # ダウンロードした秘密鍵
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    return db
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
def sendDiscord(jsonfl):
    if jsonfl is None or jsonfl == []:
        print('失敗')
        return 0
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

def getStreams(client_id, Authorization, query):
    url = 'https://api.twitch.tv/helix/streams?'+ query
    headers = {'Client-ID': client_id,
           'Authorization': "Bearer " + Authorization}
    r = requests.get(url, headers=headers)
    row_data = r.json()
    return row_data

def getHmacMessage(request):
    #メッセージを生成
    a = request.headers['Twitch-Eventsub-Message-Id']
    b = request.headers['Twitch-Eventsub-Message-Timestamp']
    c = request.data.decode('utf-8')
    return (a + b + c)

def isVaildSignature(twitchSig,MySig):
    #twiwchのシグネチャと計算結果が合っているか確認
    return twitchSig == MySig

@app.route('/',methods=["GET", "POST"])
def index():
    # 1. リクエストからヘッダとボディを取得する
    headers = request.headers
    body = request.json
    #print(headers)
    print(body)
    # 2. データベースを初期化する
    db = initializeFirestore()
    # 3. シグネチャから通信の信頼性を検証する
    TWsignature = headers.get('Twitch-Eventsub-Message-Signature')
    message = getHmacMessage(request)
    keys = getToken(db)#FireStoreから鍵を受け取る
    EXsignature = hmac.new(keys['sub_secret'].decode('utf-8'), message.decode('utf-8'), hashlib.sha256).hexdigest()
    if isVaildSignature(TWsignature,"sha256="+EXsignature) == False :
        return Response(response=body['challenge'],headers={'content-type':'text/plain'}, status=500)
    # 4. OAuthが生きているか確認する
    if isValidToken(keys.get('OAuth')) == False:#Oauthトークンの有効性を確認する
        print('If keyVaildation is false')#falseの場合に実行
        authKey = generateToken(keys['client_id'], keys['client_secret'])
        storeToken(authKey,db)
    # 5. サブスクライブのバージョンを確認する
    TWversion = headers.get('Twitch-Eventsub-Message-Type')
    if TWversion == 'te':
        return Response(response=body['challenge'],headers={'content-type':'text/plain'}, status=201)
    elif TWversion == 'revocation':
        # 再サブクスライブ申請TODO
        return Response(response=body['challenge'],headers={'content-type':'text/plain'}, status=202)
    elif TWversion == 'webhook_callback_verification':
        return Response(response=body['challenge'],headers={'content-type':'text/plain'}, status=203)
    # B. notificationの場合--情報を収集する
    user_id = body['subscription']['condition']['broadcaster_user_id']
    events = body.get('event')
    r = getStreams(keys['client_id'],keys['OAuth'],'user_id='+'126482446')
    r_list = r.get('data')
    print(r_list)
    if len(r_list) == 1:
        sendDiscord(r_list[0])
    return Response(headers={'content-type':'text/plain'}, status=200)

app.run(debug=True,port=8080)

# twitch event verify-subscription subscribe -t 200020 -F http://localhost:8080   


