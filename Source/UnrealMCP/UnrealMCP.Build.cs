// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class UnrealMCP : ModuleRules
{
    public UnrealMCP(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "Networking",
                "Sockets",
                "Slate",
                "SlateCore",
                "DeveloperSettings",
                "Projects",
                "ToolMenus",
                "UnrealEd",
                "LevelEditor",
                "BlueprintGraph",
                "GraphEditor",
                "KismetCompiler"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "Json",
                "JsonUtilities",
                "Settings",
                "InputCore",
                "PythonScriptPlugin",
                "Kismet",
                "KismetWidgets"
            }
        );
    }
}
