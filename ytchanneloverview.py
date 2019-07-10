#!/usr/bin/python3

import httplib2,os,sys,datetime

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

SORTPLAYLISTSBYDATE=False
SORTPLAYLISTSBYLIKES=True
DEBUG=False

if len(sys.argv)<2:
    raise Exception('Usage ./ytchanneloverview.py channelId [channelId channelId ...]')

def paginated(service,request):
    while request!=None:
        response=request.execute()
        yield response['items']
        request=service.list_next(request,response)
        if DEBUG:
            break
        
def getduration(video):
    duration=video['contentDetails']['duration'].replace('P','').replace('T','')
    for fieldtype in ['D','H','M','S']:
        duration=duration.replace(fieldtype,fieldtype+':')
    fields=dict(H=0,M=0,S=0)
    for field in duration.split(':')[:-1]:
        fieldtype=field[-1]
        fieldvalue=int(field[:-1])
        if fieldtype=='D':
            fields['H']+=fieldvalue*24
        else:
            fields[fieldtype]+=fieldvalue
    formatted=''
    for fieldtype in ['H','M','S']:
        fieldvalue=fields[fieldtype]
        if fieldtype=='H' and fieldvalue==0:
            continue
        formatted+=str(fieldvalue) if len(formatted)==0 else f':{fieldvalue:02d}'
    return formatted
def parsedate(date):
    return int(date.replace('-',''))

playlists=[]
ytchannels=youtube.channels()
allvideos={'snippet':{'title':'All videos'}}
channeltitle=False
for channel in sys.argv[1:]:
    listing=ytchannels.list(part='contentDetails,snippet',id=channel)
    for data in paginated(ytchannels,listing):
        channeltitle=data[0]['snippet']['title']
        allvideos['id']=data[0]['contentDetails']['relatedPlaylists']['uploads']
        playlists.append(allvideos)
ytplaylists=youtube.playlists()
for channel in sys.argv[1:]:
    listing=ytplaylists.list(channelId=channel,maxResults=50,part='snippet')
    for playlistpage in paginated(ytplaylists,listing):
        for playlist in playlistpage:
            playlists.append(playlist)
        print(str(len(playlists))+' playlists...')
if DEBUG:
    playlists=playlists[:9]
ytitems=youtube.playlistItems()
videos=set()
i=0
for playlist in playlists:
    videoids=[]
    listing=ytitems.list(playlistId=playlist['id'],maxResults=50,part='snippet')
    for itempage in paginated(ytitems,listing):
        for item in itempage:
            videoid=item['snippet']['resourceId']['videoId']
            videoids.append(videoid)
            videos.add(videoid)
    playlist['videoids']=videoids
    i+=1
    print(str(int(100*i/len(playlists)))+'% playlists...')
ytvideos=youtube.videos()
videodata={}
videos=list(videos)
while len(videos)>0:
    print(str(int(len(videos)/50))+' video pages left...')
    batch=videos[:50]
    videos=videos[50:]
    query=''
    for videoid in batch:
        query+=videoid+','
    query=query[:-1]
    parts='snippet,statistics,id,contentDetails'
    listing=ytvideos.list(part=parts,maxResults=50,id=query)
    for videopage in paginated(ytvideos,listing):
        for video in videopage:
            videodata[video['id']]=video
for video in videodata:
    data=videodata[video]
    statistics=data['statistics']
    data['lpd']=float(statistics['likeCount'])/(float(statistics['dislikeCount'])+1) if 'likeCount' in statistics and 'dislikeCount' in statistics else -9000
remove=[]
for playlist in playlists:
    if len(playlist['videoids'])==0:
        remove.append(playlist)
for empty in remove:
  playlists.remove(empty)
remove=[]
for playlist in playlists:
  playlist['videos']=[]
  rating=[]
  lastupdate=False
  for videoid in playlist['videoids']:
    if not videoid in videodata:
      continue
    video=videodata[videoid]
    playlist['videos'].append(video)
    rating.append(video['lpd'])
    publishedat=video['snippet']['publishedAt'][:10]
    if lastupdate==False or parsedate(publishedat)>parsedate(lastupdate):
      lastupdate=publishedat
  if len(rating)==0:
    remove.append(playlist)
    continue
  playlist['lpd']=sorted(rating)[int(len(rating)/2)]
  if lastupdate!=False:
    playlist['lastupdate']='0' if lastupdate==False else lastupdate 
for empty in remove:
  playlists.remove(empty)
body=''
toc='Playlists:<br/>'
playlists.remove(allvideos)
if SORTPLAYLISTSBYLIKES:
    playlists=sorted(playlists,key=lambda x:x['lpd'],reverse=True)
elif SORTPLAYLISTSBYDATE:
    playlists=sorted(playlists,key=lambda x:x['lastupdate'],reverse=True)
playlists.insert(0,allvideos)
for playlist in playlists:
    title=playlist['snippet']['title']
    pid=playlist['id']
    toc+=f'<a href="#{pid}">{title}</a>'
    toc+=f' ({playlist["lastupdate"]}, {int(playlist["lpd"])}lpd)<br/>'
    playlistvideos=playlist['videos']
    if SORTPLAYLISTSBYDATE:
        playlistvideos=sorted(playlistvideos,key=lambda x:x['snippet']['publishedAt'])
    elif SORTPLAYLISTSBYLIKES:
        playlistvideos=sorted(playlistvideos,key=lambda x:x['lpd'],reverse=True)
    body+='<span id="{}">{}</span> (updated {}, {}lpd, <a href="https://www.youtube.com/playlist?list={}">link</a>)'.format(pid,title,playlist['lastupdate'],int(playlist['lpd']),pid)
    body+='<br/>'
    for video in playlistvideos:
        videotitle=f"[{getduration(video)}] {video['snippet']['title']}"
        href='https://www.youtube.com/watch?v='+video['id']
        anchor='<a href="{}" target="_blank">{}</a> {}'
        body+=anchor.format(href,videotitle,int(video['lpd']))
        body+='<br/>'
    body+='<br/>'
print(f'''<html>
<head><title>{channeltitle} (YouTube channel overview)</title></head>
<body>
Channel id(s): {str(sys.argv[1:])}.<br>
Generated in {datetime.datetime.today().strftime('%d/%m/%Y')}.<br/>
<br/>
{toc}
<br/>
{body}
</body>
</html>''',file=open('output.html','w'))
