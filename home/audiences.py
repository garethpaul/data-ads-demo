import json
# TODO: Fix * imports
from django.shortcuts import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from twitter_ads.client import Client
from twitter_ads.audience import TailoredAudience
from twitter_ads.http import Request
from twitter_ads.cursor import Cursor
from twitter_ads.error import Error
import base64


@login_required
def handler(request):
    """
    Returns account page handler page for given request
    """
    context = {"request": request}
    return render_to_response(
        'audiences.html',
        context,
        context_instance=RequestContext(request))


@login_required
def new(request):
    """
    Returns a new TA path to hold the bucket location.
    """
    client = Client(
        settings.SOCIAL_AUTH_TWITTER_KEY,
        settings.SOCIAL_AUTH_TWITTER_SECRET,
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_TOKEN_SECRET)
    account_id = request.GET.get("account_id", "")
    name = request.GET.get("name", "")
    resource = '/0/accounts/' + account_id + '/tailored_audiences'
    params = {'name': name, 'list_type': 'HANDLE'}
    json_data = {}
    try:
        request = Request(client, 'post', resource, params=params).perform()
        # return audience.id to use
        ta_id = request.body['data']['id']
        json_data = {
            "valid": True,
            "account_id": account_id,
            "name": name,
            "id": str(ta_id)}
    except Error as e:
        json_data["response"] = e.details
        json_data["valid"] = False
    return HttpResponse(json.dumps(json_data), content_type="application/json")


@login_required
def change(request):
    """
    Returns a change to TA to upload a bucket location.
    """
    client = Client(
        settings.SOCIAL_AUTH_TWITTER_KEY,
        settings.SOCIAL_AUTH_TWITTER_SECRET,
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_TOKEN_SECRET)
    account_id = request.GET.get("account_id", "")
    identifier = request.GET.get("id", "")
    input_file_path = request.GET.get("input_file_path", "")
    # Update With location
    resource = '/0/accounts/' + account_id + '/tailored_audience_changes'
    params = {
        'tailored_audience_id': identifier,
        'input_file_path': base64.b64decode(input_file_path),
        'operation': "ADD"}
    json_data = {}
    try:
        request = Request(client, 'post', resource, params=params).perform()
        json_data["account_id"] = account_id
        json_data["data"] = request.body["data"]


    except Error as e:
        json_data["error"] = e.details
    return HttpResponse(json.dumps(json_data), content_type="application/json")
