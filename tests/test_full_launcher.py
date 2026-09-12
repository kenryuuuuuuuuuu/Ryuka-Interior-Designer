"""W08-F scope preservation, entry choices, and fixed comparison conditions."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from guest_launcher import models,update,walkthrough,config,comparison

class FullLauncherTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def project(self,name,scope):
  p=self.root/name;p.mkdir();(p/'RyukaInterior.uproject').write_text('{}')
  (p/'import-verification.json').write_text(json.dumps(dict(scopeId=scope,unrealImportVerified=True)))
  (p/'walkthrough-verification.json').write_text('{"configured":true}')
  return p
 def test_scopes_and_existing_guest_are_valid(self):
  for scope in ('guest','home','whole'):self.assertTrue(models.inspect_project(self.project(scope,scope)).valid)
 def test_entry_choices_follow_model_capability_and_rooms(self):
  p=self.project('whole','whole')
  self.assertEqual(walkthrough.entry_options(p),['resume'])
  (p/'walkthrough.json').write_text(json.dumps(dict(launcherEntrySelection=True,rooms={'room-1f-19':{},'room-1f-02':{}})))
  self.assertEqual(walkthrough.entry_options(p),['resume','home','guest'])
  (p/'walkthrough.json').write_text(json.dumps(dict(launcherEntrySelection=True,rooms={'room-1f-02':{}})))
  self.assertEqual(walkthrough.entry_options(p),['resume','guest'])
 def run_fake_update(self,scope,returned_scope=None,exit_code=0):
  p=self.project('old',scope);out=self.root/'new';out.mkdir()
  def run(argv,*args,**kwargs):
   self.assertEqual(argv[argv.index('--scope')+1],scope)
   self.project('new/ue',returned_scope or scope)
   (out/'refresh.json').write_text('{"status":"complete"}')
   (out/'ue/state-transfer-verification.json').write_text('{"statePreserved":true,"geometryVerified":true}')
   return CompletedProcess(argv,exit_code)
  cfg=config.LauncherConfig(currentModel='untouched')
  with patch.object(update.runner,'run_logged',side_effect=run):result=update.run_update(cfg,p,out)
  self.assertEqual(cfg.currentModel,'untouched');return result
 def test_whole_update_keeps_scope(self):self.assertTrue(self.run_fake_update('whole').ok)
 def test_home_update_keeps_scope(self):self.assertTrue(self.run_fake_update('home').ok)
 def test_guest_update_keeps_scope(self):self.assertTrue(self.run_fake_update('guest').ok)
 def test_wrong_result_scope_is_not_accepted(self):self.assertFalse(self.run_fake_update('whole','guest').ok)
 def test_failed_process_is_not_accepted(self):self.assertFalse(self.run_fake_update('whole',exit_code=1).ok)
 def test_fixed_active_lights_and_other_surfaces_are_verified(self):
  state={'activeRoomId':'a','roomStates':{'a':{'variant':'natural','fixtures':{'lamp':{'on':True}},'surfaceOverrides':{}},'b':{'variant':'natural','fixtures':{},'surfaceOverrides':{'wall':{'variant':'warm'}}}}}
  after=copy.deepcopy(state);after['roomStates']['a']['variant']='warm';f=self.root/'warm.json';f.write_text(json.dumps(after))
  images=[{'variant':'warm','conditions':'warm.json'}]
  self.assertIsNone(comparison._verify_ab(self.root,state,images))
  after['roomStates']['a']['fixtures']={};f.write_text(json.dumps(after));self.assertIsNotNone(comparison._verify_ab(self.root,state,images))
  after=copy.deepcopy(state);after['roomStates']['a']['variant']='warm';after['roomStates']['b']['surfaceOverrides']={};f.write_text(json.dumps(after));self.assertIsNotNone(comparison._verify_ab(self.root,state,images))

 def test_model_window_constructs_without_tk_method_collision(self):
  import tkinter as tk
  from types import SimpleNamespace
  from guest_launcher import app
  try:root=tk.Tk()
  except tk.TclError:self.skipTest('No display available')
  self.addCleanup(root.destroy);root.withdraw()
  with patch.object(models,'detect_candidates',return_value=[]):
   w=app.ChooseModelWindow(SimpleNamespace(root=root,cfg=config.LauncherConfig()))
   w.withdraw();root.update_idletasks();self.assertTrue(w.winfo_exists());w.destroy()
