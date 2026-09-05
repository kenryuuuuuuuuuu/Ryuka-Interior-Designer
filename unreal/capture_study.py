"""Editor-only offscreen QA capture, launched with -ExecCmds (not a commandlet)."""
from pathlib import Path
import json
import time
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Generated/House')
camera=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if a.get_actor_label()=='Camera_guest_LDK')
unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for command in ('r.ScreenPercentage 100','sg.GlobalIlluminationQuality 4','sg.ReflectionQuality 4',
                'r.HighResScreenshotDelay 64','r.Lumen.ScreenProbeGather.Temporal.MaxFramesAccumulated 32'):
    unreal.SystemLibrary.execute_console_command(world,command)
job=json.loads((project/'capture-job.json').read_text(encoding='utf-8'))
destination=project/'Saved'/(job['name']+'.png')
unreal.AutomationLibrary.finish_loading_before_screenshot()
start=time.monotonic()
task=None


def tick(delta):
    global task
    elapsed=time.monotonic()-start
    if task is None and elapsed>30:
        task=unreal.AutomationLibrary.take_high_res_screenshot(1600,900,str(destination),camera=camera,delay=3.0)
    if (destination.is_file() and elapsed>40) or elapsed>180:
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.SystemLibrary.quit_editor()


handle=unreal.register_slate_post_tick_callback(tick)
