"""
Apple Push Notification Service
Documentation is available on the iOS Developer Library:
https://developer.apple.com/library/content/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/APNSOverview.html
"""
import asyncio

from aioapns import (
    APNs,
    NotificationRequest,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
)

from . import models, payload
from .conf import get_manager
from .exceptions import APNSServerError, APNSUnsupportedPriority

DEFAULT_TTL = 2592000
VALID_PRIORITIES = (PRIORITY_NORMAL, PRIORITY_HIGH)


def _apns_create_socket(application_id=None):
    use_sandbox = get_manager().get_apns_use_sandbox(application_id)
    if not get_manager().has_auth_token_creds(application_id):
        cert = get_manager().get_apns_certificate(application_id)
        client = APNs(client_cert=cert, use_sandbox=use_sandbox,)
    else:
        key_path, key_id, team_id = get_manager().get_apns_auth_creds(application_id)
        topic = (get_manager().get_apns_topic(application_id=application_id),)
        client = APNs(
            key=key_path, key_id=key_id, team_id=team_id, topic=topic, use_sandbox=use_sandbox,
        )
    return client


def _apns_prepare(
    token,
    alert,
    application_id=None,
    badge=None,
    sound=None,
    category=None,
    content_available=False,
    action_loc_key=None,
    loc_key=None,
    loc_args=(),
    extra=None,
    mutable_content=False,
    thread_id=None,
    url_args=None,
):

    if action_loc_key or loc_key or loc_args:
        apns2_alert = payload.PayloadAlert(
            body=alert if alert else {},
            body_localized_key=loc_key,
            body_localized_args=loc_args,
            action_localized_key=action_loc_key,
        )
    else:
        apns2_alert = alert

    if callable(badge):
        badge = badge(token)

    return payload.Payload(
        alert=apns2_alert,
        badge=badge,
        sound=sound,
        category=category,
        url_args=url_args,
        custom=extra,
        thread_id=thread_id,
        content_available=content_available,
        mutable_content=mutable_content,
    )


def _apns_send(registration_id, alert, batch=False, application_id=None, **kwargs):
    # If there's no loop, catch the RuntimeError and create a loop first
    client = try_get_loop(func=_apns_create_socket, application_id=application_id)

    notification_kwargs = {}
    prepare_kwarg_list = [
        'application_id',
        'badge',
        'sound',
        'category',
        'content_available',
        'action_loc_key',
        'loc_key',
        'loc_args',
        'extra',
        'mutable_content',
        'thread_id',
        'url_args',
    ]
    prepare_kwargs = {key: kwargs.get(key) for key in prepare_kwarg_list if kwargs.get(key)}

    time_to_live = None
    # if "expiration" is given, subtract the current time from it to get a TTL value in seconds
    expiration = kwargs.pop('expiration', None)
    if expiration:
        time_to_live = expiration

    # if time_to_live isn"t specified use 1 month from now
    notification_kwargs['time_to_live'] = kwargs.pop('time_to_live', time_to_live)
    if not notification_kwargs['time_to_live']:
        notification_kwargs['time_to_live'] = DEFAULT_TTL

    priority = kwargs.pop('priority', PRIORITY_NORMAL)
    try:
        VALID_PRIORITIES.index(str(priority))
        notification_kwargs['priority'] = priority
    except ValueError:
        raise APNSUnsupportedPriority(f'Unsupported priority {priority}')

    notification_kwargs['collapse_key'] = kwargs.pop('collapse_id', None)

    if batch:
        data = {
            rid: NotificationRequest(
                rid,  # device_token
                _apns_prepare(rid, alert, **prepare_kwargs).dict(),  # message
                **notification_kwargs,
            )
            for rid in registration_id
        }
        # returns a dictionary mapping each token to its result. That
        # result is either "Success" or the reason for the failure.
        return send_async(client, data)
    else:
        message = _apns_prepare(registration_id, alert, **prepare_kwargs).dict()  # message
        request = NotificationRequest(
            registration_id, message, **notification_kwargs,  # device_token
        )
        print(request)
        return send_async(client, {registration_id: request})


def send_async(client, requests):
    response = []

    async def execute():
        try:
            notifications = {}
            for token, request in requests.items():
                notifications[request.notification_id] = token
                send_requests = [client.send_notification(request)]

            res = await asyncio.wait(send_requests)
            task = res[0].pop()
            r = task.result()
            if not r.is_successful:
                await error_handling_async(r, notifications[r.notification_id])
            response.append(r)
        except Exception as e:
            raise e

    loop = try_get_loop()
    loop.run_until_complete(execute())
    return response


def try_get_loop(*args, func=None, **kwargs):
    try:
        return func(*args, **kwargs) if func else asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return func(*args, **kwargs) if func else loop


async def error_handling_async(response, registration_id):
    if response.status == '410' and response.description == 'Unregistered':
        await remove_devices((registration_id,))


async def remove_devices(inactive_tokens):
    models.APNSDevice.objects.filter(registration_id__in=inactive_tokens).update(active=False)


def apns_send_message(registration_id, alert, application_id=None, **kwargs):
    """
    Sends an APNS notification to a single registration_id.
    This will send the notification as form data.
    If sending multiple notifications, it is more efficient to use
    apns_send_bulk_message()

    Note that if set alert should always be a string. If it is not set,
    it won't be included in the notification. You will need to pass None
    to this for silent notifications.
    """

    try:
        return _apns_send(registration_id, alert, application_id=application_id, **kwargs)
    # TODO - Figure out what exceptions need to be caught here
    except Exception as e:
        print(e)
        if str(e) == 'Unregistered':
            await remove_devices((registration_id,))

        raise APNSServerError(status=str(e))


def apns_send_bulk_message(registration_ids, alert, application_id=None, **kwargs):
    """
    Sends an APNS notification to one or more registration_ids.
    The registration_ids argument needs to be a list.

    Note that if set alert should always be a string. If it is not set,
    it won't be included in the notification. You will need to pass None
    to this for silent notifications.
    """

    return _apns_send(registration_ids, alert, batch=True, application_id=application_id, **kwargs)
