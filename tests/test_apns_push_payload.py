from unittest import mock
try:
    from unittest.mock import AsyncMock
except ImportError:
    from asyncmock import AsyncMock

from aioapns import PRIORITY_HIGH
from django.test import TestCase

import push_notifications.apns
from push_notifications.apns import _apns_send
from push_notifications.exceptions import APNSUnsupportedPriority


class APNSPushPayloadTest(TestCase):
    def test_push_payload(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    _apns_send(
                        "123",
                        "Hello world",
                        badge=1,
                        sound="chime",
                        extra={"custom_data": 12345},
                        time_to_live=3,
                    )

                    self.assertTrue(s.called)
                    args, kargs = s.call_args
                    self.assertEqual(args[0], '123')
                    self.assertEqual(args[1]['aps']['alert'], 'Hello world')
                    self.assertEqual(args[1]['aps']['sound'], 'chime')
                    self.assertEqual(args[1]['aps']['badge'], 1)
                    self.assertEqual(args[1]['custom_data'], 12345)
                    self.assertEqual(kargs['time_to_live'], 3)

    def test_push_payload_with_thread_id(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    _apns_send(
                        '123',
                        'Hello world',
                        thread_id='565',
                        sound='chime',
                        extra={'custom_data': 12345},
                        expiration=3,
                    )
                    args, kargs = s.call_args
                    print(args)
                    self.assertEqual(args[0], '123')
                    self.assertEqual(args[1]['aps']['alert'], 'Hello world')
                    self.assertEqual(args[1]['aps']['sound'], 'chime')
                    self.assertEqual(args[1]['aps']['thread-id'], '565')
                    self.assertEqual(args[1]['custom_data'], 12345)
                    self.assertEqual(kargs['time_to_live'], 3)

    def test_push_payload_with_alert_dict(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    _apns_send(
                        '123',
                        alert={'title': 't1', 'body': 'b1'},
                        sound='chime',
                        extra={'custom_data': 12345},
                        expiration=3,
                    )
                    args, kargs = s.call_args
                    print(args)
                    self.assertEqual(args[0], '123')
                    self.assertEqual(args[1]['aps']['alert']['body'], 'b1')
                    self.assertEqual(args[1]['aps']['alert']['title'], 't1')
                    self.assertEqual(args[1]['aps']['sound'], 'chime')
                    self.assertEqual(args[1]['custom_data'], 12345)
                    self.assertEqual(kargs['time_to_live'], 3)

    def test_localised_push_with_empty_body(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    _apns_send('123', None, loc_key='TEST_LOC_KEY', time_to_live=3)
                    args, kargs = s.call_args
                    print(args)
                    self.assertEqual(args[0], '123')
                    self.assertEqual(args[1]['aps']['alert']['loc-key'], 'TEST_LOC_KEY')
                    self.assertEqual(kargs['time_to_live'], 3)

    def test_using_extra(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    _apns_send(
                        '123', 'sample', extra={'foo': 'bar'}, time_to_live=30, priority=10,
                    )
                    args, kargs = s.call_args
                    self.assertEqual(args[0], '123')
                    self.assertEqual(args[1]['aps']['alert'], 'sample')
                    self.assertEqual(kargs['time_to_live'], 30)
                    self.assertEqual(kargs['priority'], int(PRIORITY_HIGH))
                    self.assertEqual(args[1]['foo'], 'bar')

    def test_bad_priority(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    self.assertRaises(
                        APNSUnsupportedPriority, _apns_send, '123', '_' * 2049, priority=24,
                    )
                    s.assert_has_calls([])

    def test_collapse_id(self):
        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    s.return_value=None
                    _apns_send('123', 'sample', collapse_id='456789')
                    args, kargs = s.call_args
                    assert s.called
                    self.assertEqual(args[0], '123')
                    self.assertEqual(args[1]['aps']['alert'], 'sample')
                    self.assertEqual(kargs['collapse_key'], '456789')
