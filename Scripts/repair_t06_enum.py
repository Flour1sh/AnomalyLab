"""One-time repair of empty T00 enum using existing UE editor DLL exports.
No C++ is generated/compiled. Layout checks use installed UE 5.8 Python headers.
The native FText move constructor transfers ownership of the by-value argument.
"""
import unreal,ctypes,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'Scripts'))
import build_t04 as h
from editor_toolset.toolsets.blueprint import BlueprintTools as B
e=h.load('/Game/Core/Types/EPrototypeRoundState')
g=unreal.BlueprintEditorLibrary.find_event_graph(h.load(h.BOX_PATH))
probe=h.create(g,['EPrototypeRoundState'],0,0,include=('switch','EPrototypeRoundState'))
count=len(h.output_pins(probe));unreal.BlueprintGraphEditor.get_graph_editor(g).remove_nodes([probe])
assert count in (0,4),count
if count==0:
 backup=root/'Saved/T06/EPrototypeRoundState.before.uasset'
 if not backup.exists():shutil.copy2(root/'Content/Core/Types/EPrototypeRoundState.uasset',backup)
 assert type(e).__basicsize__==24
 ptr=ctypes.c_void_p.from_address(id(e)+16).value
 assert format(ptr,'016x') in repr(e).lower()
 lib=ctypes.WinDLL('UnrealEditor-UnrealEd.dll');core=ctypes.WinDLL('UnrealEditor-Core.dll')
 add=getattr(lib,'?AddNewEnumeratorForUserDefinedEnum@FEnumEditorUtils@@SAXPEAVUUserDefinedEnum@@@Z');add.argtypes=[ctypes.c_void_p];add.restype=None
 rename=getattr(lib,'?SetEnumeratorDisplayName@FEnumEditorUtils@@SA_NPEAVUUserDefinedEnum@@HVFText@@@Z');rename.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];rename.restype=ctypes.c_bool
 move=getattr(core,'??0FText@@QEAA@$$QEAV0@@Z');move.argtypes=[ctypes.c_void_p,ctypes.c_void_p];move.restype=ctypes.c_void_p
 for i,name in enumerate(('Ready','Revealing','OutcomeActive','Ended')):
  add(ptr)
  text=unreal.Text(name);assert type(text).__basicsize__ in (32,40),type(text).__basicsize__
  buf=ctypes.create_string_buffer(24);move(ctypes.addressof(buf),id(text)+16)
  assert rename(ptr,i,ctypes.addressof(buf))
 assert h.ASSETS.save_loaded_asset(e,False)
unreal.log('[T06] PREFLIGHT PASS - round enum repaired')

