using UnrealBuildTool;
public class RyukaInteriorEditorTarget : TargetRules {
 public RyukaInteriorEditorTarget(TargetInfo Target) : base(Target) {
  Type=TargetType.Editor; DefaultBuildSettings=BuildSettingsVersion.Latest; bUseSharedPCHs=false;
  ExtraModuleNames.Add("RyukaInterior");
 }
}
