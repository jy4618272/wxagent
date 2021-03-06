import json

from PyQt5.QtCore import *
from PyQt5.QtDBus import *

from .basecontroller import BaseController, Chatroom
from .logiccontroller import LogicController
from .wxcommon import *
from .txmessage import TXMessage

from .xmpprelay import XmppRelay


class XmppCallProxy(QObject):
    def __init__(self, ctrl, parent=None):
        super(XmppCallProxy, self).__init__(parent)
        self.ctrl = ctrl
        return

    def friendExists(self, friendId):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rtab.funcName(), friendId)

    def send_message(self, mto, mbody):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rtab.funcName(), mto, mbody)

    def muc_send_message(self, mto, mbody):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rtab.funcName(), mto, mbody)

    def muc_number_peers(self, group_number):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rtab.funcName(), group_number)

    def muc_invite(self, group_number, peer):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rtab.funcName(), group_number, peer)

    def create_muc2(self, room_ident, title):
        qDebug('hehree')
        return self.ctrl.remoteCall(self.ctrl.rtab.funcName(), room_ident, title)


class XmppController(BaseController):
    def __init__(self, rtab, parent=None):
        super(XmppController, self).__init__(rtab, parent)
        self.relay = XmppRelay()
        self.peerRelay = self.relay
        from .secfg import peer_xmpp_user
        self.relay.peer_user = peer_xmpp_user
        self.initRelay()
        self.relay.xmpp = XmppCallProxy(self)
        self.chnamemap = {}
        return

    def initSession(self):
        return

    def replyMessage(self, msgo):
        qDebug(str(msgo['context']['channel']).encode())
        from .secfg import peer_xmpp_user
        qDebug(str(msgo).encode())
        channel = msgo['context']['channel']
        nchannel = self.relay._roomify_name(channel)
        self.chnamemap[nchannel] = channel
        channel = nchannel

        msg = msgo['params'][0]
        msg = str(msgo)
        self.relay.sendMessage(msg, peer_xmpp_user)
        # self.relay.sendGroupMessage(msgo['params'][0], channel)
        txmsg = TXMessage()
        txmsg.FromUserName = self.peerRelay.self_user
        txmsg.Content = msgo['params'][0]
        txmsg.Content = msg
        self.dispatchGroupChat(channel, txmsg)
        return

    def updateSession(self, msgo):
        qDebug('heree')
        evt = msgo['evt']
        params = msgo['params']
        if evt == 'on_connected': self.relay.on_connected(*params)
        elif evt == 'on_disconnected': self.relay.on_disconnected(*params)
        elif evt == 'on_message': self.relay.on_message(*params)
        elif evt == 'on_muc_message': self.relay.on_muc_message(*params)
        elif evt == 'on_peer_connected': self.relay.on_peer_connected(*params)
        elif evt == 'on_peer_disconnected': self.relay.on_peer_disconnected(*params)
        elif evt == 'on_peer_enter_group': self.relay.on_peer_enter_group(*params)
        else: pass
        return

    def fillContext(self, msgo):
        msgtxt = str(msgo)
        qDebug(msgtxt.encode())
        nchannel = msgo['params'][0]
        channel = self.chnamemap[nchannel]
        qDebug(str(channel).encode())
        msgo['context'] = {'channel': channel}
        return msgo

    def dispatchGroupChat(self, channel, msg):
        groupchat = None
        mkey = channel
        mkey = self.peerRelay._roomify_name(channel)
        title = '' + str(channel)
        fmtcc = msg.Content

        if self.rtab.unichats.existContrl(mkey, self.__class__.__name__):
            groupchat = self.rtab.unichats.get(mkey, self.__class__.__name__)
        else:
            qDebug('room not found: {}'.format(mkey).encode())
            qDebug(str(self.rtab.unichats.dumpKeys()).encode())

        if mkey in self.txchatmap:
            groupchat = self.txchatmap[mkey]
            # assert groupchat is not None
        else:
            qDebug('room not found: {}'.format(mkey).encode())
            qDebug(str(self.txchatmap.keys()).encode())

        if groupchat is not None:
            # assert groupchat is not None
            # 有可能groupchat已经就绪，但对方还没有接收请求，这时发送失败，消息会丢失
            number_peers = self.peerRelay.groupNumberPeers(groupchat.group_number)
            if number_peers < 2:
                groupchat.unsend_queue.append(fmtcc)
                ### reinvite peer into group
                self.peerRelay.groupInvite(groupchat.group_number, self.peerRelay.peer_user)
            else:
                self.peerRelay.sendGroupMessage(fmtcc, groupchat.group_number)
        else:
            # TODO 如果是新创建的groupchat，则要等到groupchat可用再发，否则会丢失消息
            groupchat = self.createChatroom(msg, mkey, title)
            groupchat.unsend_queue.append(fmtcc)

        return

    def createChatroom(self, msg, mkey, title):
        group_number = ('WXU.%s' % mkey).lower()
        group_number = mkey
        group_number = self.peerRelay.createChatroom(mkey, title)
        groupchat = Chatroom()
        groupchat.group_number = group_number
        groupchat.FromUser = msg.FromUser
        groupchat.ToUser = msg.ToUser
        groupchat.FromUserName = msg.FromUserName
        self.txchatmap[mkey] = groupchat
        self.relaychatmap[group_number] = groupchat
        groupchat.title = title
        self.rtab.unichats.add(mkey, self.__class__.__name__, groupchat)

        self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        return groupchat

    def fillChatroom(self, msgo, mkey=None, title=None, group_numer=None):
        mkey = str(msgo['context']['channel'])
        qDebug(str(mkey).encode())
        title = "T: " + str(msgo['context']['channel'])
        title = str(msgo['context']['channel'])
        group_number = msgo['params'][0]

        # group_number = ('WXU.%s' % mkey).lower()
        # group_number = mkey
        # group_number = self.peerRelay.createChatroom(mkey, title)
        groupchat = Chatroom()
        groupchat.group_number = group_number
        # groupchat.FromUser = msg.FromUser
        # groupchat.ToUser = msg.ToUser
        # groupchat.FromUserName = msg.FromUserName
        groupchat.msgo = msgo
        self.txchatmap[mkey] = groupchat
        self.relaychatmap[group_number] = groupchat
        groupchat.title = title
        self.rtab.unichats.add(mkey, self.__class__.__name__, groupchat)

        # self.peerRelay.groupInvite(group_number, self.peerRelay.peer_user)

        return groupchat
