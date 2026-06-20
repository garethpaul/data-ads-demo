import json
# TODO: Fix * imports
from django.shortcuts import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout
from django.conf import settings
from twitter_ads.client import Client
from twitter_ads.campaign import LineItem
from twitter_ads.enum import PRODUCT, PLACEMENT, OBJECTIVE
from twitter_ads.error import Error

from home.ads_protocol import (
    MAX_REQUEST_BYTES,
    TwitterAdsTargetingClient,
    process_targeting_request)


@login_required
def new_targeting(request):
    """
    Creates a targeting criterion through a bounded, single-attempt POST.
    """
    def client_factory():
        return TwitterAdsTargetingClient(
            settings.SOCIAL_AUTH_TWITTER_KEY,
            settings.SOCIAL_AUTH_TWITTER_SECRET,
            settings.TWITTER_ACCESS_TOKEN,
            settings.TWITTER_ACCESS_TOKEN_SECRET,
            base_url=settings.TWITTER_ADS_API_BASE_URL)

    try:
        content_length = int(request.META.get("CONTENT_LENGTH", ""))
    except (TypeError, ValueError):
        content_length = 0
    if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
        status = 400
        json_data = {"valid": False, "error": "invalid_request"}
    else:
        status, json_data = process_targeting_request(
            request.method,
            request.META.get("CONTENT_TYPE", ""),
            request.body,
            client_factory)
    return HttpResponse(
        json.dumps(json_data),
        content_type="application/json",
        status=status)


@login_required
def new(request):
    """
    Returns a new line item
    """
    client = Client(
        settings.SOCIAL_AUTH_TWITTER_KEY,
        settings.SOCIAL_AUTH_TWITTER_SECRET,
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_TOKEN_SECRET)
    account_id = request.GET.get("account_id", "")
    campaign_id = request.GET.get("campaign_id", "")
    campaign_name = request.GET.get("name", "")
    budget = request.GET.get("budget", "")
    account_id = request.GET.get("account_id", "")
    name = request.GET.get("name", "")
    bid_amount = request.GET.get("bid_amount", "")

    json_data = {}
    try:
        account = client.accounts(account_id)
        # create your campaign
        line_item = LineItem(account)
        line_item.campaign_id = campaign_id
        line_item.name = name
        line_item.product_type = PRODUCT.PROMOTED_TWEETS
        line_item.placements = [PLACEMENT.ALL_ON_TWITTER]
        line_item.objective = OBJECTIVE.TWEET_ENGAGEMENTS
        line_item.bid_amount_local_micro = int(bid_amount) * 1000
        line_item.paused = True
        line_item.save()
        json_data = {
            "account_id": account_id,
            "campaign_name": campaign_name,
            "campaign_id": campaign_id}
    except Error as e:
        json_data["response"] = e.details
        json_data["valid"] = False

        pass
    return HttpResponse(json.dumps(json_data), content_type="application/json")


@login_required
def json_handler(request):
    """
    Returns json_data {"campaigns": [campaign_list} for given request
    """
    client = Client(
        settings.SOCIAL_AUTH_TWITTER_KEY,
        settings.SOCIAL_AUTH_TWITTER_SECRET,
        settings.TWITTER_ACCESS_TOKEN,
        settings.TWITTER_ACCESS_TOKEN_SECRET)
    account_id = request.GET.get("account_id", "")
    campaign_id = request.GET.get("campaign_id", "")
    account = client.accounts(account_id)
    # TODO: Link to Ads API Docs for LineItem.rst
    line_items = account.line_items(None, campaign_ids=campaign_id)
    line_item_list = []
    for line_item in line_items:
        name = line_item.name
        identifier = line_item.id
        objective = line_item.objective
        bid_amount = line_item.bid_amount_local_micro
        # Sometimes Bid Amount is None
        if bid_amount is not None:
            bid_amount = bid_amount / 10000
        line_item_list.append({"name": name,
                               "id": identifier,
                               "objective": objective,
                               "bid_amount": bid_amount})
    return HttpResponse(
        json.dumps(
            {
                "account_id": account_id,
                "campaign_id": campaign_id,
                "line_items": line_item_list}),
        content_type="application/json")


@login_required
def handler(request):
    """
    Returns account page handler page for given request
    """
    account_id = request.GET.get("account_id", "")
    campaign_id = request.GET.get("campaign_id", "")
    context = {
        "request": request,
        "account_id": account_id,
        "campaign_id": campaign_id}
    return render_to_response(
        'lineitems.html',
        context,
        context_instance=RequestContext(request))
