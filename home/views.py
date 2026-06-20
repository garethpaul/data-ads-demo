import datetime
import random
import csv
import json
import StringIO

from app import ton

from chart import Chart
from timeframe import Timeframe
from frequency import Frequency
from tweets import Tweets

# TODO: Fix * imports
from django.shortcuts import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie

MAX_AGE = getattr(settings, 'CACHE_CONTROL_MAX_AGE', 2592000)

# import twitter


def login(request):
    """
    Returns login page for given request
    """
    context = {"request": request}
    return render_to_response(
        'login.html',
        context,
        context_instance=RequestContext(request))


@login_required
@ensure_csrf_cookie
def home(request):
    """
    Returns home page for given request
    """
    query = request.GET.get("query", "")
    context = {"request": request, "query0": query}
    tweets = []
    return render_to_response(
        'home.html',
        context,
        context_instance=RequestContext(request))


@login_required
def query_chart(request):
    """
    Returns query chart for given request
    """
    # TODO: Move this to one line e.g. queries to query
    query = request.GET.get("query", None)
    queries = request.GET.getlist("queries[]")
    if query:
        queries = [query]

    response_chart = Chart(queries=queries, request=request).data
    response = HttpResponse(
        json.dumps(response_chart),
        content_type="application/json")
    response['Cache-Control'] = 'max-age=%d' % MAX_AGE
    return response


@login_required
def query_frequency(request):
    query = request.GET.get("query", None)
    response_data = {}
    sample = 500
    if query is not None:
        # Get Timeframe e.g. process time from request
        request_timeframe = Timeframe(
            start=request.GET.get(
                "start", None), end=request.GET.get(
                "end", None), interval=request.GET.get(
                "interval", "hour"))
        # Query GNIP and get frequency
        data = Frequency(query=query,
                         sample=sample,
                         start=request_timeframe.start,
                         end=request_timeframe.end)
        response_data["frequency"] = data.freq
        response_data["sample"] = sample
        response = HttpResponse(
            json.dumps(response_data),
            content_type="application/json")
    response['Cache-Control'] = 'max-age=%d' % MAX_AGE
    return response


@login_required
def query_tweets(request):
    """
    Returns tweet query
    """
    query_count = 10000  # int(request.GET.get("embedCount", TWEET_QUERY_COUNT))
    export = request.GET.get("export", None)
    query = request.GET.get("query", "")
    tweets = Tweets(query=query, query_count=query_count, request=request)

    response_data = {}

    if export == "ta":
        output = StringIO.StringIO()
        for t in tweets.get_data():
            user_id = t['actor']['id']
            output.write(user_id + '\n')
        ton_request = ton.TwitterTon(
            twitter_consumer_key=settings.SOCIAL_AUTH_TWITTER_KEY,
            twitter_consumer_secret=settings.SOCIAL_AUTH_TWITTER_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET)
        bytes = output.getvalue()
        ton_response = ton_request.upload_data(
            payload=bytes.encode('utf-16be'))
        output.close()
        location = ton_response['location']
        response = HttpResponse(json.dumps(
            {"location": location, "query": query}), content_type="application/json")
        return response

    elif export == "csv":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'
        writer = csv.writer(response)
        writer.writerow(['count',
                         'time',
                         'id',
                         'user_screen_name',
                         'user_id',
                         'status',
                         'retweet_count',
                         'favorite_count',
                         'is_retweet',
                         'in_reply_to_tweet_id',
                         'in_reply_to_screen_name'])
        count = 0
        for t in tweets.get_data():
            count = count + 1
            body = t['body'].encode('ascii', 'replace')
            status_id = t['id']
            status_id = status_id[status_id.rfind(':') + 1:]
            user_id = t['actor']['id']
            user_id = user_id[user_id.rfind(':') + 1:]
            writer.writerow([count,
                             t['postedTime'],
                             status_id,
                             t['actor']['preferredUsername'],
                             user_id,
                             body,
                             t['retweetCount'],
                             t['favoritesCount'],
                             'X',
                             'X',
                             'X'])
            return response
    else:
        response_data['tweets'] = tweets.get_data()
        response = HttpResponse(
            json.dumps(response_data),
            content_type="application/json")
        response['Cache-Control'] = 'max-age=%d' % MAX_AGE
        return response


def handle_query_error(e):
    """
    Returns HTTP response with an error
    """
    response_data = {}
    response_data['error'] = e.message
    response_data['response'] = e.response
    response_data['payload'] = e.payload
    return HttpResponse(
        json.dumps(response_data),
        status=400,
        content_type="application/json")


def logout(request):
    """
    Returns a redirect response and logs out user
    """
    auth_logout(request)
    return HttpResponseRedirect('/')
