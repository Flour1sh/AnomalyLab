using UnrealBuildTool;

public class AnomalyLab : ModuleRules
{
    public AnomalyLab(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "AIModule", "NavigationSystem", "Json", "UMG" });
        // Menu keyboard routing and authored Button styles use Slate directly.
        PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
    }
}
