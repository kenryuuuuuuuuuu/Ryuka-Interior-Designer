using UnrealBuildTool;
public class RyukaInterior : ModuleRules {
 public RyukaInterior(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage=PCHUsageMode.NoPCHs;
  PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","InputCore","Json","JsonUtilities"});
 }
}
