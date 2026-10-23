import tempfile
import time
import unittest
from pathlib import Path
from core_platform.native_notary import NativeNotarySessions
from core_platform.native_ron_rooms import NativeRonRooms
from core_platform.native_recording_manifest import NativeRecordingManifests, RecordingDenied

class NativeRecordingManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path=Path(self.tmp.name)/'notary.db'
        self.sessions=NativeNotarySessions(path)
        self.sessions.create('ron-1','case-1','RON','WI')
        self.rooms=NativeRonRooms(path)
        self.rooms.create('ron-1','room-1')
        self.rooms.consent('ron-1','b'*64)
        self.rooms.recording('ron-1','a'*64)
        self.manifests=NativeRecordingManifests(path)
        now=int(time.time())
        self.args=('ron-1','namespace','bucket','ron/recording.webm','a'*64,1024,now-60,now)

    def test_recording_manifest_persists_and_is_idempotent(self):
        result=self.manifests.register(*self.args)
        self.assertEqual(result,self.manifests.register(*self.args))
        self.assertFalse(result['storage_upload_verified'])
        self.assertGreater(result['retain_until'],self.args[-1]+9*365*86400)

    def test_conflicting_manifest_rejected(self):
        self.manifests.register(*self.args)
        with self.assertRaises(RecordingDenied):
            args=list(self.args)
            args[4]='c'*64
            self.manifests.register(*args)

    def test_unrecorded_session_rejected(self):
        self.sessions.create('ron-2','case-2','RON','WI')
        args=list(self.args)
        args[0]='ron-2'
        with self.assertRaises(RecordingDenied):
            self.manifests.register(*args)
