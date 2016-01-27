import json
# TODO: Fix * imports
from django.shortcuts import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout
from django.conf import settings
from twitter_ads.client import Client
from twitter_ads.campaign import TargetingCriteria, LineItem
from twitter_ads.enum import PRODUCT, PLACEMENT, OBJECTIVE
from twitter_ads.error import Error

@login_required
def new_targeting(request):
    """
    Creates a new
    """
    line_item_id = request.REQUEST.get("line_item_id", "")
    account_id = request.REQUEST.get("account_id", "")
    targeting_value = request.REQUEST.get("targeting_value");
    targeting_type = "BEHAVIOR_EXPANDED"
    json_data = {}
    try:
        client = Client(settings.SOCIAL_AUTH_TWITTER_KEY, settings.SOCIAL_AUTH_TWITTER_SECRET, settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
        account = client.accounts(account_id)
        targeting_criteria = TargetingCriteria(account)
        targeting_criteria.line_item_id = line_item_id
        targeting_criteria.targeting_type = targeting_type
        targeting_criteria.targeting_value = targeting_value
        if targeting_value == "TAILORED_AUDIENCE":
            targeting_criteria.tailored_audience_type = "FLEXIBLE"
        targeting_criteria.save()
        json_data = {"valid": True, "account_id": account_id, "line_item_id": line_item_id, "targeting_value": targeting_value}
    except Exception as e:
        # Get first item from list of errors
        json_data["response"] = e.response.body
        #print type(e.response.headers.all)
        json_data["valid"] = False
        # passing to push the json_data to the browser
        pass
    return HttpResponse(json.dumps(json_data), content_type="application/json")

@login_required
def new(request):
    """
    Returns a new campaign
    """
    client = Client(settings.SOCIAL_AUTH_TWITTER_KEY, settings.SOCIAL_AUTH_TWITTER_SECRET, settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
    account_id = request.REQUEST.get("account_id", "")
    campaign_id = request.REQUEST.get("campaign_id", "")
    campaign_name = request.REQUEST.get("name", "")
    budget = request.REQUEST.get("budget", "")
    account_id = request.REQUEST.get("account_id", "")
    name = request.REQUEST.get("name", "")
    bid_amount = request.REQUEST.get("bid_amount", "")

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
        line_item.bid_amount_local_micro = int(bid_amount)*1000
        line_item.paused = True
        line_item.save()
        json_data = {"account_id": account_id, "campaign_name": campaign_name, "campaign_id": campaign_id}
    except Error as e:
        json_data = e.details
        pass
    return HttpResponse(json.dumps(json_data), content_type="application/json")

@login_required
def json_handler(request):
    """
    Returns json_data {"campaigns": [campaign_list} for given request
    """
    client = Client(settings.SOCIAL_AUTH_TWITTER_KEY, settings.SOCIAL_AUTH_TWITTER_SECRET, settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
    account_id = request.REQUEST.get("account_id", "")
    campaign_id = request.REQUEST.get("campaign_id", "")
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
        if bid_amount != None:
            bid_amount = bid_amount/10000
        line_item_list.append({"name": name, "id": identifier, "objective": objective, "bid_amount": bid_amount})
    return HttpResponse(json.dumps({"account_id": account_id, "campaign_id": campaign_id, "line_items": line_item_list}), content_type="application/json")

@login_required
def handler(request):
    """
    Returns account page handler page for given request
    """
    account_id = request.REQUEST.get("account_id", "")
    campaign_id = request.REQUEST.get("campaign_id", "")
    context = {"request": request, "account_id": account_id, "campaign_id": campaign_id}
    return render_to_response('lineitems.html', context, context_instance=RequestContext(request))
