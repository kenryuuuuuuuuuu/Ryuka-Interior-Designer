using UnrealBuildTool;
public class RyukaInteriorTarget : TargetRules {
 public RyukaInteriorTarget(TargetInfo Target) : base(Target) {
  Type=TargetType.Game; DefaultBuildSettings=BuildSettingsVersion.Latest; bUseSharedPCHs=false;
  ExtraModuleNames.Add("RyukaInterior");
 }
}
