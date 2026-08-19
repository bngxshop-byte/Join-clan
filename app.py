from flask import Flask, jsonify
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

app = Flask(__name__)

K = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
V = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def Encrypt_API(data):
    data = bytes.fromhex(data)
    cipher = AES.new(K, AES.MODE_CBC, V)
    return cipher.encrypt(pad(data, AES.block_size)).hex()

def Encrypt_ID(num):
    num = int(num)
    result = []
    while True:
        value = num & 127
        num >>= 7
        if num:
            value |= 128
        result.append(value)
        if not num:
            break
    return bytes(result).hex()

def Get_JWT(uid, password):
    try:
        url = f"https://jwt-tmk.vercel.app/GeneRate-Jwt?uid={uid}&password={password}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.text.strip()
        return None
    except:
        return None

def Headers(token, payload):
    return {
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "Authorization": f"Bearer {token}",
        "Content-Length": str(len(payload) // 2),
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "clientbp.ggblueshark.com",
        "ReleaseVersion": "OB54",
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2022.3.47f1"
    }

def Payload(clan):
    return Encrypt_API(f"08{Encrypt_ID(clan)}1007")

def Request(url, token, payload):
    return requests.post(
        url,
        headers=Headers(token, payload),
        data=bytes.fromhex(payload)
    )

@app.route("/join/<clan>/<uid>/<password>")
def JoiN(clan, uid, password):
    token = Get_JWT(uid, password)

    if not token:
        return jsonify({"error": "JWT FAILED"}), 400

    payload = Payload(clan)

    try:
        res = Request(
            "https://clientbp.ggblueshark.com/RequestJoinClan",
            token,
            payload
        )

        return {
            "status": res.status_code,
            "jwt_used": token,
            "response": res.text
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/exit/<clan>/<uid>/<password>")
def ExiT(clan, uid, password):
    token = Get_JWT(uid, password)

    if not token:
        return jsonify({"error": "JWT FAILED"}), 400

    payload = Payload(clan)

    try:
        res = Request(
            "https://clientbp.ggblueshark.com/QuitClan",
            token,
            payload
        )

        return {
            "status": res.status_code,
            "jwt_used": token,
            "response": res.text
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def HomE():
    return {"status": "API READY"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
