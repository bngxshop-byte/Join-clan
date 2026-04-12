import httpx
import time
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import json
from flask import Flask, request, jsonify
from datetime import datetime
import data_pb2
import encode_id_clan_pb2
import reqClan_pb2
import jwt as pyjwt

# ====== الإعدادات الأساسية ======
freefire_version = "OB53"
key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
JWT_REGEX = re.compile(r'(eyJ[A-Za-z0-9_\-\.=]+)')

# ====== الدوال الأساسية ======
def get_jwt_token_from_api(uid, password):
    url1 = f"https://jwt-liard-eight.vercel.app/get?uid={uid}&password={password}"
    try:
        response = httpx.get(url1, timeout=15.0)
        if response.status_code == 200:
            response_data = response.json()
            jwt_token = response_data.get("token")
            if jwt_token and isinstance(jwt_token, str):
                return jwt_token
        print(f"JWT Token API Error: Status {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"JWT Token API Error: {e}")

    # الطريقة البديلة
    try:
        data_param = f"{uid}:{password}"
        url2 = f"https://api.freefireservice.dnc.su/oauth/account:login?data={data_param}"
        response = httpx.get(url2, timeout=15.0)
        token_candidate = None
        try:
            j = response.json()
            for k in ("token", "jwt", "access_token", "data", "auth"):
                v = j.get(k)
                if isinstance(v, str) and v.startswith("ey"):
                    token_candidate = v
                    break
        except Exception:
            pass
        if not token_candidate:
            m = JWT_REGEX.search(response.text)
            if m:
                token_candidate = m.group(1)
        if not token_candidate:
            for hv in response.headers.values():
                m = JWT_REGEX.search(hv)
                if m:
                    token_candidate = m.group(1)
                    break
        return token_candidate
    except Exception as e:
        print(f"Alternative JWT Token API Error: {e}")
        return None

def get_region_from_jwt(jwt_token):
    try:
        decoded = pyjwt.decode(jwt_token, options={"verify_signature": False})
        lock_region = decoded.get('lock_region', 'ME')
        return lock_region.upper()
    except Exception as e:
        print(f"Region decode error: {e}")
        return 'ME'

def get_region_url(region=None):
    if region is None:
        region = 'ME'
    region = region.upper()
    if region == "IND":
        return "https://client.ind.freefiremobile.com"
    elif region in ["BR", "US", "SAC", "NA"]:
        return "https://client.us.freefiremobile.com"
    else:
        return "https://clientbp.ggblueshark.com"
def create_quit_payload(clan_id):
    message = reqClan_pb2.MyMessage()
    message.field_1 = int(clan_id)
    serialized_data = message.SerializeToString()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(serialized_data, AES.block_size))
    return encrypted_data

def create_join_payload(clan_id):
    message = reqClan_pb2.MyMessage()
    message.field_1 = int(clan_id)
    serialized_data = message.SerializeToString()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(serialized_data, AES.block_size))
    return encrypted_data

def get_clan_info(base_url, jwt_token, clan_id):
    try:
        json_data = json.dumps({"1": int(clan_id), "2": 1})
        my_data = encode_id_clan_pb2.MyData()
        json_obj = json.loads(json_data)
        my_data.field1 = json_obj["1"]
        my_data.field2 = json_obj["2"]
        data_bytes = my_data.SerializeToString()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_info_data = cipher.encrypt(pad(data_bytes, 16))
        info_url = f"{base_url}/GetClanInfoByClanID"
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {jwt_token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": freefire_version,
            "Content-Type": "application/octet-stream",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
            "Host": base_url.replace("https://", ""),
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        with httpx.Client(timeout=30.0) as client_info:
            info_response = client_info.post(info_url, headers=headers, content=encrypted_info_data)
        if info_response.status_code == 200:
            resp_info = data_pb2.response()
            resp_info.ParseFromString(info_response.content)
            return {
                "clan_name": getattr(resp_info, "special_code", "Unknown"),
                "clan_level": getattr(resp_info, "level", "Unknown")
            }
        else:
            return {"clan_name": "Unknown", "clan_level": "Unknown"}
    except Exception as e:
        print(f"Clan info error: {e}")
        return {"clan_name": "Unknown", "clan_level": "Unknown"}
def quit_clan_with_credentials(uid, password, clan_id, region=None):
    print(f"بدء عملية الخروج من الكلان UID: {uid}")

    jwt_token = get_jwt_token_from_api(uid, password)
    if not jwt_token:
        return {"success": False, "message": "فشل في الحصول على التوكن", "uid": uid}

    if region is None:
        region = get_region_from_jwt(jwt_token)
    else:
        region = region.upper()

    base_url = get_region_url(region)
    encrypted_data = create_quit_payload(clan_id)

    url = f"{base_url}/QuitClan"
    host = base_url.replace("https://", "")

    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": freefire_version,
        "Content-Type": "application/octet-stream",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Host": host,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, content=encrypted_data)

        if response.status_code == 200:
            return {
                "success": True,
                "message": "تم الخروج من الكلان بنجاح",
                "uid": uid,
                "clan_id": clan_id,
                "region": region,
                "status_code": response.status_code,
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "message": f"فشل الخروج من الكلان، رمز الحالة: {response.status_code}",
                "uid": uid,
                "clan_id": clan_id,
                "region": region,
                "status_code": response.status_code,
                "timestamp": time.time()
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"خطأ في الخادم: {str(e)}",
            "uid": uid,
            "clan_id": clan_id
        }

    
def join_clan_with_credentials(uid, password, clan_id, region=None):
    print(f"بدء العملية بحساب UID: {uid}")
    jwt_token = get_jwt_token_from_api(uid, password)
    if not jwt_token:
        return {"success": False, "message": "فشل في الحصول على التوكن", "uid": uid}
    if region is None:
        region = get_region_from_jwt(jwt_token)
    else:
        region = region.upper()
    base_url = get_region_url(region)
    clan_info = get_clan_info(base_url, jwt_token, clan_id)
    encrypted_data = create_join_payload(clan_id)
    url = f"{base_url}/RequestJoinClan"
    host = base_url.replace("https://", "")
    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": freefire_version,
        "Content-Type": "application/octet-stream",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Host": host,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, content=encrypted_data)
        if response.status_code == 200:
            result = {
                "success": True,
                "message": "تم إرسال طلب الانضمام بنجاح",
                "uid": uid,
                "clan_id": clan_id,
                "clan_name": clan_info.get("clan_name", "Unknown"),
                "clan_level": clan_info.get("clan_level", "Unknown"),
                "region": region,
                "status_code": response.status_code,
                "timestamp": time.time()
            }
        else:
            result = {
                "success": False,
                "message": f"فشل إرسال طلب الانضمام، رمز الحالة: {response.status_code}",
                "uid": uid,
                "clan_id": clan_id,
                "clan_name": clan_info.get("clan_name", "Unknown"),
                "region": region,
                "status_code": response.status_code,
                "timestamp": time.time()
            }
        return result
    except Exception as e:
        return {"success": False, "message": f"حدث خطأ في الخادم: {str(e)}", "uid": uid, "clan_id": clan_id, "error": str(e)}

# ====== Flask API مع GET query params ======
app = Flask(__name__)

@app.route("/quit_clan", methods=["GET"])
def quit_clan_api():
    try:
        uid = request.args.get("uid")
        password = request.args.get("password")
        clan_id = request.args.get("clan_id")
        region = request.args.get("region", "ME")

        if not uid or not password or not clan_id:
            return jsonify({
                "success": False,
                "message": "يجب توفير uid و password و clan_id"
            }), 400

        try:
            uid = int(uid)
            clan_id = int(clan_id)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "uid و clan_id يجب أن يكونا أرقام"
            }), 400

        result = quit_clan_with_credentials(uid, password, clan_id, region)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"حدث خطأ: {str(e)}"
        }), 500


@app.route("/join_clan", methods=["GET"])
def join_clan_api():
    try:
        uid = request.args.get("uid")
        password = request.args.get("password")
        clan_id = request.args.get("clan_id")
        region = request.args.get("region", "ME")  # اختياري

        if not uid or not password or not clan_id:
            return jsonify({"success": False, "message": "يجب توفير uid و password و clan_id"}), 400

        # تحويل uid و clan_id لأرقام
        try:
            uid = int(uid)
            clan_id = int(clan_id)
        except ValueError:
            return jsonify({"success": False, "message": "uid و clan_id يجب أن تكون أرقام"}), 400

        result = join_clan_with_credentials(uid, password, clan_id, region)
        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "message": f"حدث خطأ: {str(e)}"}), 500

# ====== تشغيل Flask ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=20165)
