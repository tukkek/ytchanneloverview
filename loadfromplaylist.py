#!/usr/bin/python3

import httplib2
import sys,os

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0
To make this sample run you will need to populate the client_secrets.json file
found at:
   %s
with information from the {{ Cloud Console }}
{{ https://cloud.google.com/console }}
For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# This OAuth 2.0 access scope allows for read-only access to the authenticated
# user's account, but not other types of account access.
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
  message=MISSING_CLIENT_SECRETS_MESSAGE,
  scope=YOUTUBE_READONLY_SCOPE)

storage = Storage("%s-oauth2.json" % sys.argv[0])
credentials = storage.get()

if credentials is None or credentials.invalid:
  flags = argparser.parse_args()
  credentials = run_flow(flow, storage, flags)

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
  http=credentials.authorize(httplib2.Http()))

'''BOILERPLATE FINISH'''

DEBUG=False

def paginated(service,request):
    while request!=None:
        response=request.execute()
        yield response['items']
        request=service.list_next(request,response)
        if DEBUG:
            break

if len(sys.argv)<2:
    raise Exception('Usage ./loadfromplaylist.py playlistUrl [playlistUrl playlistUrl...]')

ytitems=youtube.playlistItems()
videosids=list()
for url in sys.argv[1:]:
    for itempage in paginated(ytitems,ytitems.list(playlistId=url[url.rfind('=')+1:],maxResults=50,part='snippet')):
        for item in itempage:
            videoid=item['snippet']['resourceId']['videoId']
            videosids.append(videoid)
ytvideos=youtube.videos()
videosids=list(set(videosids))
channels=[]
while len(videosids)>0:
    batch=videosids[:50]
    videosids=videosids[50:]
    query=''
    for videoid in batch:
        query+=videoid+','
    query=query[:-1]
    for videopage in paginated(ytvideos,ytvideos.list(part='snippet,statistics,id',maxResults=50,id=query)):
        for video in videopage:
            channels.append(video['snippet']['channelId'])
print('Result (from {} videos):'.format(len(channels)))
print()
output=''
for channel in set(channels):
    output+=channel+' ' 
print(output)
