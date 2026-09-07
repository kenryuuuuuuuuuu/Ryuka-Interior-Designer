import json
from pathlib import Path
import unreal
p=Path(unreal.Paths.project_dir()).resolve()
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Generated/House')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
count=unreal.WalkthroughLibrary.prepare(world)
world.get_world_settings().set_editor_property('default_game_mode',unreal.WalkthroughGameMode)
assert unreal.EditorAssetLibrary.save_directory('/Game/Generated',only_if_is_dirty=False,recursive=True)
assert level.save_current_level()
(p/'walkthrough-verification.json').write_text(json.dumps(dict(collisionMeshes=count,configured=True,runtimeVerified=False)),encoding='utf-8')
