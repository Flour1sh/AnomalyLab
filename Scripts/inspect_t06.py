import sys, json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
import build_t04 as h
from editor_toolset.toolsets.blueprint import BlueprintTools as B
result={}
for path in (h.CHARACTER_PATH,h.HUD_PATH,h.INTERACTION_PATH):
    bp=h.load(path)
    data={'variables':h.member_names(bp),'graphs':{}}
    for g in B.list_graphs(bp):
        data['graphs'][g.get_name()]=[{'name':n.get_name(),'title':str(n.get_node_title()),'pins':[{'name':h.pin_name(p),'value':str(p.get_pin_value()),'links':[q.get_owning_node().get_name()+'.'+h.pin_name(q) for q in p.list_connected_pins()]} for p in h.input_pins(n)+h.output_pins(n)]} for n in B.find_nodes(g)]
    result[path]=data
result['widgets']=[(str(v.widget_name),v.widget.get_class().get_name()) for v in h.UMG.call_method('GetWidgets',(h.load(h.HUD_PATH),)).widgets]
out=ROOT/'Saved/T06';out.mkdir(parents=True,exist_ok=True)
(out/'baseline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
unreal.log('[T06] PREFLIGHT PASS')
