import aiohttp
import requests
import hmac
import json
import base64
from hashlib import sha1
import time
from time import time as timestamp
from time import timezone, sleep
from typing import BinaryIO
from locale import getdefaultlocale as locale
import concurrent.futures
import asyncio

import random
import string

from .lib.util import exceptions, device, objects, helpers
from .socket import Callbacks, SocketHandler

#not all functions work properly

#gen_msg_sig by SirLez with Bovonos
def gen_msg_sig():
    return base64.b64encode(bytes.fromhex("22") + hmac.new(bytes.fromhex(str(int(time.time()))), "22".encode("utf-8"),
                                                           sha1).digest()).decode()
#generate captcha from samino
def captcha():
        captcha = "".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + "_-", k=462)).replace("--", "-")
        return captcha

device = device.DeviceGenerator()

class Client(Callbacks, SocketHandler):
    def __init__(self, profile: str = None, certificatePath = None, socket_trace = False, socketDebugging = False):
        self.api = 'https://service.narvii.com/api/v1'
        self.configured = None

        self.device_id = device.device_id
        self.user_agent = device.user_agent

        SocketHandler.__init__(self, self, socket_trace=socket_trace, debug=socketDebugging)
        Callbacks.__init__(self, self)

        self.sid = None
        self.certificatePath = certificatePath
        self.profile = profile
        self.auid = None
        self.headers = {
            "NDCLANG": "ru",
            "NDC-MSG-SIG": gen_msg_sig(),
            "NDCDEVICEID": f"{self.device_id}",
            "SMDEVICEID": "b89d9a00-f78e-46a3-bd54-6507d68b343c",
            "NDCAUTH": f"sid={self.sid}",
            "Accept-Language": "ru-RU",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"{self.device_id}",
            "Host": "service.narvii.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }
        self.s_headers = {"NDCDEVICEID": self.device_id}
        self.web_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
            "x-requested-with": "xmlhttprequest"
        }
        self.userId = None
        self.comId = None
        self.json = None
        self.uid = None
    def web_login(self, email: str, password: str):
        data = {
            "auth_type": 0,
            "email": email,
            "recaptcha_challenge": captcha(),
            "recaptcha_version": "v3",
            "secret": password
        }
        response = requests.post("https://aminoapps.com/api/auth", json=data)
        if response.status_code != 200:
            print(json.loads(response.text))
        else:
            if json.loads(response.text)["result"].get("isMember") is None:
                print("Login failed")
                return json.loads(response.text)
            self.web_headers = response.headers
            self.sid = response.headers["set-cookie"]
            try: 
                self.sid = self.sid[0: self.sid.index(";")]
            except: 
                self.sid = self.sid
            self.uid = response.json()["result"]["uid"]
            self.headers["NDCAUTH"] = self.sid
            self.s_headers["NDCAUTH"] = self.sid
            subclient.SubClient().headers["NDCAUTH"] = self.sid
            if self.profile != None:
                try:
                    self.userId = self.get_chat_id(code=self.profile)['chatId']
                    self.comId = self.get_chat_id(code=self.profile)['comId']
                except:
                    self.profile = None
            return response.status_code
    def get_chat_id(self, code: str):
        url = f"{self.api}/g/s/link-resolution?q={code}"
        response = requests.get(url=url, headers=self.headers).json()['linkInfoV2']['extensions']['linkInfo']
        return {"comId": response['ndcId'], "chatId": response['objectId']}

    def join_community(self, comId: str, invitationId: str = None):
        url = f"{self.api}/x{comId}/s/community/join"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.post(url=url, headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200:
            return exceptions.CheckException(json.loads(response.text))
        else:
            return response.status_code
    def leave_community(self, comId: str):
        url = f"{self.api}/x{comId}/s/community/leave"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.post(url=url, headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200:
            return exceptions.CheckException(json.loads(response.text))
        else:
            return response.status_code
    def get_user_info(self, userId: str):
        url = f"{self.api}/g/s/user-profile/{userId}"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(url=url, headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200:
            return exceptions.CheckException(json.loads(response.text))
        else:
            return objects.UserProfile(json.loads(response.text)["userProfile"]).UserProfile
    def get_from_deviceid(self, deviceId: str):
        url=f"{self.api}/g/s/auid?deviceId={deviceId}"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(url=url, verify=self.certificatePath)
        if response.status_code != 200:
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return json.loads(response.text)["auid"]
    def join_chat(self, chatId: str):
        url = f"{self.api}/x{self.comId}/s/chat/thread/{chatId}/member/{self.userId}"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.post(url=url, headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200:
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return json.loads(response.text)
    def leave_chat(self, chatId: str):
        url = f"{self.api}/x{self.comId}/s/chat/thread/{chatId}/member/{self.userId}"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.delete(url=url, headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200:
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return json.loads(response.text)
    #from SAmino
    def start_chat(self, userId: str = None, title: str = None, message: str = None, content: str = None):
        if isinstance(userId, str):
            userIds = [userId]
        elif isinstance(userId, list):
            userIds = userId
        else:
            print(':(')

        data = json.dumps({
            "title": title,
            "inviteeUids": userIds,
            "initialMessageContent": message,
            "content": content,
        })
        req = requests.post(f'{self.api}/g/s/chat/thread', headers=self.web_headers, data=data)
        if req.status_code != 200: 
            print(req.json())
        return req.json()
    #from SAmino
    def invite_to_chat(self, chatId: str = None, userId: str = None):
        if isinstance(userId, str):
            userIds = [userId]
        elif isinstance(userId, list):
            userIds = userId
        else:
            print(':( ')

        data = json.dumps({"uids": userIds})
        req = requests.post(f'{self.api}/g/s/chat/thread/{chatId}/member/invite', data=data, headers=self.web_headers)
        if req.status_code != 200: 
            print(req.json())
        return req.json()
    def send_message(self, chatId: str, message: str = None, messageType: int = 0, file: BinaryIO = None, fileType: str = None, replyTo: str = None, mentionUserIds: list = None, stickerId: str = None, embedId: str = None, embedType: int = None, embedLink: str = None, embedTitle: str = None, embedContent: str = None, embedImage: BinaryIO = None):
        """
        **Parameters**
            - **message** : Message to be sent
            - **chatId** : ID of the Chat.
            - **file** : File to be sent.
            - **fileType** : Type of the file.
                - ``audio``, ``image``, ``gif``
            - **messageType** : Type of the Message.
            - **mentionUserIds** : List of User IDS to mention. '@' needed in the Message.
            - **replyTo** : Message ID to reply to.
            - **stickerId** : Sticker ID to be sent.
            - **embedTitle** : Title of the Embed.
            - **embedContent** : Content of the Embed.
            - **embedLink** : Link of the Embed.
            - **embedImage** : Image of the Embed.
            - **embedId** : ID of the Embed.

        **Returns**
            - **Success** : 200 (int)

            - **Fail** : :meth:`Exceptions <amino.lib.util.exceptions>`
        """

        if message is not None and file is None:
            message = message.replace("<$", "‎‏").replace("$>", "‬‭")

        mentions = []
        if mentionUserIds:
            for mention_uid in mentionUserIds:
                mentions.append({"uid": mention_uid})

        if embedImage:
            embedImage = [[100, self.upload_media(embedImage, "image"), None]]

        data = {
            "type": messageType,
            "content": message,
            "clientRefId": int(timestamp() / 10 % 1000000000),
            "attachedObject": {
                "objectId": embedId,
                "objectType": embedType,
                "link": embedLink,
                "title": embedTitle,
                "content": embedContent,
                "mediaList": embedImage
            },
            "extensions": {"mentionedArray": mentions},
            "timestamp": int(timestamp() * 1000)
        }

        if replyTo: data["replyMessageId"] = replyTo

        if stickerId:
            data["content"] = None
            data["stickerId"] = stickerId
            data["type"] = 3

        if file:
            data["content"] = None
            if fileType == "audio":
                data["type"] = 2
                data["mediaType"] = 110

            elif fileType == "image":
                data["mediaType"] = 100
                data["mediaUploadValueContentType"] = "image/jpg"
                data["mediaUhqEnabled"] = True

            elif fileType == "gif":
                data["mediaType"] = 100
                data["mediaUploadValueContentType"] = "image/gif"
                data["mediaUhqEnabled"] = True

            else: raise exceptions.SpecifyType(fileType)

            data["mediaUploadValue"] = base64.b64encode(file.read()).decode()

        data = json.dumps(data)
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.post(f"{self.api}/x{self.comId}/s/chat/thread/{chatId}/message", headers=self.headers, data=data, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return response.status_code
    def get_chat_threads(self, start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/g/s/chat/thread?type=joined-me&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.ThreadList(json.loads(response.text)["threadList"]).ThreadList
    def get_chat_messages(self, chatId: str, size: int = 25, pageToken: str = None):
        if pageToken is not None: url = f"{self.api}/g/s/chat/thread/{chatId}/message?v=2&pagingType=t&pageToken={pageToken}&size={size}"
        else: url = f"{self.api}/g/s/chat/thread/{chatId}/message?v=2&pagingType=t&size={size}"
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(url, headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return GetMessages(json.loads(response.text)).GetMessages
    def get_message_info(self, chatId: str, messageId: str):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/g/s/chat/thread/{chatId}/message/{messageId}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return Message(json.loads(response.text)["message"]).Message
    def login(self, email: str, password: str):
        data1 = json.dumps({
            "email": email,
            "v": 2,
            "secret": f"0 {password}",
            "deviceID": f"{self.device_id}",
            "clientType": 100,
            "action": "normal",
            "timestamp": int(timestamp() * 1000)
        })
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.post(f"{self.api}/g/s/auth/login", headers=self.headers_login, data=data1, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            self.json = json.loads(response.text)
            self.sid = self.json["sid"]
    def get_online_users(self, start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/x{self.comId}/s/live-layer?topic=ndtopic:x{self.comId}:online-members&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.UserProfileCountList(json.loads(response.text)).UserProfileCountList
    def get_chat_users(self, chatId: str, start: int = 0, size: int = 25):
        response = requests.get(f"{self.api}/x{self.comId}/s/chat/thread/{chatId}/member?start={start}&size={size}&type=default&cv=1.2", headers=self.s_headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.UserProfileList(json.loads(response.text)["memberList"]).UserProfileList
    def get_public_chat_threads(self, type: str = "recommended", start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/x{self.comId}/s/chat/thread?type=public-all&filterType={type}&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.ThreadList(json.loads(response.text)["threadList"]).ThreadList
    def get_notifications(self, start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/x{self.comId}/s/notification?pagingType=t&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.NotificationList(json.loads(response.text)["notificationList"]).NotificationList
    def get_invite_codes(self, status: str = "normal", start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/g/s-x{self.comId}/community/invitation?status={status}&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.InviteCodeList(json.loads(response.text)["communityInvitationList"]).InviteCodeList
    def generate_invite_code(self, duration: int = 0, force: bool = True):
        data = json.dumps({
            "duration": duration,
            "force": force,
            "timestamp": int(timestamp() * 1000)
        })
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.post(f"{self.api}/g/s-x{self.comId}/community/invitation", headers=self.headers, data=data, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.InviteCode(json.loads(response.text)["communityInvitation"]).InviteCode
    def search_users(self, nickname: str, start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/x{self.comId}/s/user-profile?type=name&q={nickname}&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.UserProfileList(json.loads(response.text)["userProfileList"]).UserProfileList
    def sub_clients(self, start: int = 0, size: int = 25):
        self.headers["NDC-MSG-SIG"] = gen_msg_sig()
        response = requests.get(f"{self.api}/g/s/community/joined?v=1&start={start}&size={size}", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.CommunityList(json.loads(response.text)["communityList"]).CommunityList
    def get_community_info(self, comId: str):
        response = requests.get(f"{self.api}/g/s-x{comId}/community/info?withInfluencerList=1&withTopicList=true&influencerListOrderStrategy=fansCount", headers=self.headers, verify=self.certificatePath)
        if response.status_code != 200: 
            return exceptions.CheckException(json.loads(response.text))
        else: 
            return objects.Community(json.loads(response.text)["community"]).Community
    def kick(self, userId: str, chatId: str, allowRejoin: bool = True):
        if allowRejoin: allowRejoin = 1
        if not allowRejoin: allowRejoin = 0
        response = requests.delete(f"{self.api}/x{self.comId}/s/chat/thread/{chatId}/member/{userId}?allowRejoin={allowRejoin}", headers=self.s_headers, verify=self.certificatePath)
        if response.status_code != 200: return exceptions.CheckException(json.loads(response.text))
        else: return response.status_code
    def get_chat_thread(self, chatId: str):
        """
        Get the Chat Object from an Chat ID.

        **Parameters**
            - **chatId** : ID of the Chat.

        **Returns**
            - **Success** : :meth:`Chat Object <amino.lib.util.objects.Thread>`

            - **Fail** : :meth:`Exceptions <amino.lib.util.exceptions>`
        """
        response = requests.get(f"{self.api}/x{self.comId}/s/chat/thread/{chatId}", headers=self.s_headers, verify=self.certificatePath)
        if response.status_code != 200: return exceptions.CheckException(json.loads(response.text))
        else: return objects.Thread(json.loads(response.text)["thread"]).Thread
    def get_public_chat_threads(self, type: str = "recommended", start: int = 0, size: int = 25):
        """
        List of Public Chats of the Community.

        **Parameters**
            - *start* : Where to start the list.
            - *size* : Size of the list.

        **Returns**
            - **Success** : :meth:`Chat List <amino.lib.util.objects.ThreadList>`

            - **Fail** : :meth:`Exceptions <amino.lib.util.exceptions>`
        """
        response = requests.get(f"{self.api}/x{self.comId}/s/chat/thread?type=public-all&filterType={type}&start={start}&size={size}", headers=self.s_headers, verify=self.certificatePath)
        if response.status_code != 200: return exceptions.CheckException(json.loads(response.text))
        else: return objects.ThreadList(json.loads(response.text)["threadList"]).ThreadList
    def get_all_users(self, type: str = "recent", start: int = 0, size: int = 25):
        if type == "recent": response = requests.get(f"{self.api}/x{self.comId}/s/user-profile?type=recent&start={start}&size={size}", headers=self.s_headers, verify=self.certificatePath)
        elif type == "banned": response = requests.get(f"{self.api}/x{self.comId}/s/user-profile?type=banned&start={start}&size={size}", headers=self.s_headers, verify=self.certificatePath)
        elif type == "featured": response = requests.get(f"{self.api}/x{self.comId}/s/user-profile?type=featured&start={start}&size={size}", headers=self.s_headers, verify=self.certificatePath)
        elif type == "leaders": response = requests.get(f"{self.api}/x{self.comId}/s/user-profile?type=leaders&start={start}&size={size}", headers=self.s_headers, verify=self.certificatePath)
        elif type == "curators": response = requests.get(f"{self.api}/x{self.comId}/s/user-profile?type=curators&start={start}&size={size}", headers=self.s_headers, verify=self.certificatePath)
        else: raise exceptions.WrongType(type)

        if response.status_code != 200: return exceptions.CheckException(json.loads(response.text))
        else: return objects.UserProfileCountList(json.loads(response.text)).UserProfileCountList
#fix Amino.py 1.2.17 by Minori
#https://service.narvii.com/api/v1/g/s/chat/thread-check/human-readable?ndcIds=0%2C{comId} - ?
#SAmino - https://github.com/SirLez/SAmino
#Amino.py - https://github.com/Slimakoi/Amino.py