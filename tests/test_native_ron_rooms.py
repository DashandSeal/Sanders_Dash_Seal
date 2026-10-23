import tempfile
import unittest
from pathlib import Path
from core_platform.native_notary import NativeNotarySessions
from core_platform.native_ron_rooms import NativeRonRooms, RoomDenied

class NativeRonRoomTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'notary.db'
        self.sessions=NativeNotarySessions(path)
        self.sessions.create('ron-1','case-1','RON','WI')
        self.sessions.create('enotary-1','case-2','E_NOTARY','CO')
        self.rooms=NativeRonRooms(path)

    def test_consent_and_recording_order(self):
        self.assertEqual(self.rooms.create('ron-1','room-1')['state'],'AWAITING_CONSENT')
        with self.assertRaises(RoomDenied):
            self.rooms.recording('ron-1','a'*64)
        self.assertEqual(self.rooms.consent('ron-1','b'*64)['state'],'CONSENT_RECORDED')
        self.assertEqual(self.rooms.recording('ron-1','a'*64)['state'],'RECORDING_INDEXED')
        self.assertEqual(NativeRonRooms(self.rooms.path).get('ron-1')['recording_digest'],'a'*64)

    def test_enotary_cannot_create_ron_room(self):
        with self.assertRaises(RoomDenied):
            self.rooms.create('enotary-1','room-2')

    def test_duplicate_and_cancelled_room_denied(self):
        self.rooms.create('ron-1','room-1')
        with self.assertRaises(RoomDenied):
            self.rooms.create('ron-1','room-1')
        self.sessions.create('ron-2','case-3','RON','WI')
        self.sessions.cancel('ron-2')
        with self.assertRaises(RoomDenied):
            self.rooms.create('ron-2','room-2')
