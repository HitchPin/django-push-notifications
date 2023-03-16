from unittest import mock
try:
    from unittest.mock import AsyncMock
except ImportError:
    from asyncmock import AsyncMock

from aioapns import PRIORITY_NORMAL
from django.conf import settings
from django.test import TestCase, override_settings

from push_notifications.apns import _apns_prepare
from push_notifications.exceptions import APNSError
from push_notifications.models import APNSDevice


class APNSModelTestCase(TestCase):

    def _create_devices(self, devices):
        for device in devices:
            APNSDevice.objects.create(registration_id=device)

    @override_settings()
    def test_apns_send_bulk_message(self):
        self._create_devices(["abc", "def"])

        # legacy conf manager requires a value
        settings.PUSH_NOTIFICATIONS_SETTINGS.update({
            "APNS_CERTIFICATE": "/path/to/apns/certificate.pem"
        })

        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    APNSDevice.objects.all().send_message("Hello world", expiration=1)

                    message_sig = _apns_prepare("abc", "Hello world").dict()
                    print(f'Call count: {s.call_count}')
                    args, kargs = s.call_args
                    calls = s.call_args_list
                    self.assertEqual(calls[0], mock.call("abc", message_sig, priority=PRIORITY_NORMAL, collapse_key=None, time_to_live=1))
                    self.assertEqual(calls[1], mock.call("def", message_sig, priority=PRIORITY_NORMAL, collapse_key=None, time_to_live=1))
                    self.assertEqual(args[1]['aps']['alert'], "Hello world")
                    self.assertEqual(kargs["time_to_live"], 1)

    def test_apns_send_message_extra(self):
        self._create_devices(['abc'])

        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    APNSDevice.objects.get().send_message(
                        'Hello world', expiration=2, priority=5, extra={'foo': 'bar'}
                    )
                    args, kargs = s.call_args
                    self.assertEqual(args[0], 'abc')
                    self.assertEqual(args[1]['aps']['alert'], 'Hello world')
                    self.assertEqual(args[1]['foo'], 'bar')
                    self.assertEqual(kargs['priority'], int(PRIORITY_NORMAL))
                    self.assertEqual(kargs['time_to_live'], 2)

    def test_apns_send_message(self):
        self._create_devices(["abc"])

        with mock.patch('push_notifications.apns.APNs.__init__', return_value=None):
            with mock.patch('push_notifications.apns.APNs.send_notification', new=AsyncMock()):
                with mock.patch('push_notifications.apns.NotificationRequest') as s:
                    APNSDevice.objects.get().send_message("Hello world", expiration=1)
                    args, kargs = s.call_args
                    self.assertEqual(args[0], 'abc')
                    self.assertEqual(args[1]['aps']['alert'], 'Hello world')
                    self.assertEqual(kargs['time_to_live'], 1)


# These are for testing the following exceptions
# from apns2.errors import BadTopic, PayloadTooLarge, Unregistered
#    def test_apns_send_message_to_single_device_with_error(self):
#        # these errors are device specific, device.active will be set false
#        devices = ["abc"]
#        self._create_devices(devices)
#
#        with mock.patch("push_notifications.apns._apns_send") as s:
#            s.side_effect = Unregistered
#            device = APNSDevice.objects.get(registration_id="abc")
#            with self.assertRaises(APNSError) as ae:
#                device.send_message("Hello World!")
#            self.assertEqual(ae.exception.status, "Unregistered")
#            self.assertFalse(APNSDevice.objects.get(registration_id="abc").active)
#
#    def test_apns_send_message_to_several_devices_with_error(self):
#        # these errors are device specific, device.active will be set false
#        devices = ["abc", "def", "ghi"]
#        expected_exceptions_statuses = ["PayloadTooLarge", "BadTopic", "Unregistered"]
#        self._create_devices(devices)
#
#        with mock.patch("push_notifications.apns._apns_send") as s:
#            s.side_effect = [PayloadTooLarge, BadTopic, Unregistered]
#
#            for idx, token in enumerate(devices):
#                device = APNSDevice.objects.get(registration_id=token)
#                with self.assertRaises(APNSError) as ae:
#                    device.send_message("Hello World!")
#                self.assertEqual(ae.exception.status, expected_exceptions_statuses[idx])
#
#                if idx == 2:
#                    self.assertFalse(APNSDevice.objects.get(registration_id=token).active)
#                else:
#                    self.assertTrue(APNSDevice.objects.get(registration_id=token).active)
#
#    def test_apns_send_message_to_bulk_devices_with_error(self):
#        # these errors are device specific, device.active will be set false
#        devices = ["abc", "def", "ghi"]
#        results = {"abc": "PayloadTooLarge", "def": "BadTopic", "ghi": "Unregistered"}
#        self._create_devices(devices)
#
#        with mock.patch("push_notifications.apns._apns_send") as s:
#            s.return_value = results
#
#            results = APNSDevice.objects.all().send_message("Hello World!")
#
#            for idx, token in enumerate(devices):
#                if idx == 2:
#                    self.assertFalse(APNSDevice.objects.get(registration_id=token).active)
#                else:
#                    self.assertTrue(APNSDevice.objects.get(registration_id=token).active)
