"""Editor-only offscreen QA capture, launched with -ExecCmds (not a commandlet)."""
from pathlib import Path
import json
import hashlib
import time
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Generated/House')
context_path=project/'site-context.json'
if context_path.exists():
    report=json.loads((project/'import-verification.json').read_text(encoding='utf-8'))
    if hashlib.sha256(context_path.read_bytes()).hexdigest()!=report['siteContext']['sha256']:
        raise RuntimeError('Local context changed; regenerate before capture')
    from site_context import verify_scene
    verify_scene(json.loads(context_path.read_text(encoding='utf-8-sig')))
job=json.loads((project/'capture-job.json').read_text(encoding='utf-8'))
if (project/'study-state.json').exists():
    import study_controls
    if job.get('sunCase') is not None: study_controls.set_sun_case(job['sunCase'])
    state=study_controls.current_state()
    if job.get('variant'): state['variant']=job['variant']
    if job.get('elevation') is not None:
        state.pop('solar',None)
        state['elevationDeg']=job['elevation']
    study_controls.apply_state(state)
    state=study_controls.current_state()
    (project/'Saved'/(job['name']+'-conditions.json')).write_text(json.dumps(state,indent=2),encoding='utf-8')
camera=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if a.get_actor_label()=='Camera_guest_LDK')
# W07-G3: honour a per-capture viewpoint. `study-state.json`'s own camera
# (a saved/selected room viewpoint) frames whatever room this capture is
# for -- water rooms, the hall, etc. -- rather than always the LDK camera.
# apply_state() above already moved the Camera_guest_LDK ACTOR to the
# state's camera when state['camera'] is non-null, so the actor's current
# transform is the right one to render from either way.
unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for command in ('r.ScreenPercentage 100','sg.GlobalIlluminationQuality 4','sg.ReflectionQuality 4',
                'r.HighResScreenshotDelay 64','r.Lumen.ScreenProbeGather.Temporal.MaxFramesAccumulated 32'):
    unreal.SystemLibrary.execute_console_command(world,command)
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
