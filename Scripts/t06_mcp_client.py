"""Localhost MCP adapter; never uses UI automation or saves game assets."""
import json
from pathlib import Path
from t05_mcp_client import Client
OUT=Path(__file__).resolve().parent.parent/'Saved/T06'
class Session:
 def __init__(self):self.client=Client()
 def call(self,toolset,tool,**args):
  r=self.client.tool('call_tool',{'toolset_name':toolset,'tool_name':tool,'arguments':args})
  if r.get('isError'):raise RuntimeError(r)
  items=[x['text'] for x in r.get('content',[]) if x['type']=='text']
  try:d=json.loads(items[0])
  except Exception:return items
  return d.get('returnValue',d)
 def editor(self,name,**args):return self.call('EditorToolset.EditorAppToolset',name,**args)
 def find(self,name=''):return self.call('editor_toolset.toolsets.scene.SceneTools','find_actors',name=name,tag='',collision_channels=[])
 def props(self,obj,*names):return json.loads(self.call('editor_toolset.toolsets.object.ObjectTools','get_properties',instance=obj,properties=list(names)))
 def listprops(self,obj):return self.call('editor_toolset.toolsets.object.ObjectTools','list_properties',instance=obj)
 def set(self,obj,**values):return self.call('editor_toolset.toolsets.object.ObjectTools','set_properties',instance=obj,values=json.dumps(values))
 def logs(self,pattern):return self.call('EditorToolset.LogsToolset','GetLogEntries',category='',pattern=pattern,maxEntries=100)
if __name__=='__main__':
 s=Session();a=s.find('BoxSpawner');print('SPAWNERS',a)
 (OUT/'live_editor_spawners.json').write_text(json.dumps(a,indent=2),encoding='utf-8')
 for obj in a:print('PROPS',s.props(obj,'CurrentBox','RoundState','ThreatsResolved','MaxThreats','BoxClass','CurrentSpawnRetryCount'))
 print('BOXES',s.find('AnomalyBox'))
 print('START',s.editor('StartPIE',options={'bSimulate':False,'playMode':'PlayMode_InViewPort','warmupSeconds':1}))
 print('PIE_SPAWNERS',s.find('BoxSpawner'))
 print('PIE_BOXES',s.find('AnomalyBox'))
 print('PLAYERS',s.find('FirstPersonCharacter'))
