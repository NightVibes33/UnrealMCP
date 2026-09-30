#include "MCPCommandHandlers.h"
#include "IPythonScriptPlugin.h"
#include "PythonScriptTypes.h"

#include "ActorEditorUtils.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "MCPFileLogger.h"
#include "HAL/PlatformFilemanager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Guid.h"
#include "MCPConstants.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"


//
// FMCPGetSceneInfoHandler
//
TSharedPtr<FJsonObject> FMCPGetSceneInfoHandler::Execute(const TSharedPtr<FJsonObject> &Params, FSocket *ClientSocket)
{
    MCP_LOG_INFO("Handling get_scene_info command");

    UWorld *World = GEditor->GetEditorWorldContext().World();
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> ActorsArray;

    int32 ActorCount = 0;
    int32 TotalActorCount = 0;
    bool bLimitReached = false;

    // First count the total number of actors
    for (TActorIterator<AActor> CountIt(World); CountIt; ++CountIt)
    {
        TotalActorCount++;
    }

    // Then collect actor info up to the limit
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor *Actor = *It;
        TSharedPtr<FJsonObject> ActorInfo = MakeShared<FJsonObject>();
        ActorInfo->SetStringField("name", Actor->GetName());
        ActorInfo->SetStringField("type", Actor->GetClass()->GetName());

        // Add the actor label (user-facing friendly name)
        ActorInfo->SetStringField("label", Actor->GetActorLabel());

        // Add location
        FVector Location = Actor->GetActorLocation();
        TArray<TSharedPtr<FJsonValue>> LocationArray;
        LocationArray.Add(MakeShared<FJsonValueNumber>(Location.X));
        LocationArray.Add(MakeShared<FJsonValueNumber>(Location.Y));
        LocationArray.Add(MakeShared<FJsonValueNumber>(Location.Z));
        ActorInfo->SetArrayField("location", LocationArray);

        ActorsArray.Add(MakeShared<FJsonValueObject>(ActorInfo));
        ActorCount++;
        if (ActorCount >= MCPConstants::MAX_ACTORS_IN_SCENE_INFO)
        {
            bLimitReached = true;
            MCP_LOG_WARNING("Actor limit reached (%d). Only returning %d of %d actors.",
                            MCPConstants::MAX_ACTORS_IN_SCENE_INFO, ActorCount, TotalActorCount);
            break; // Limit for performance
        }
    }

    Result->SetStringField("level", World->GetName());
    Result->SetNumberField("actor_count", TotalActorCount);
    Result->SetNumberField("returned_actor_count", ActorCount);
    Result->SetBoolField("limit_reached", bLimitReached);
    Result->SetArrayField("actors", ActorsArray);

    MCP_LOG_INFO("Sending get_scene_info response with %d/%d actors", ActorCount, TotalActorCount);

    return CreateSuccessResponse(Result);
}

//
// FMCPCreateObjectHandler
//
TSharedPtr<FJsonObject> FMCPCreateObjectHandler::Execute(const TSharedPtr<FJsonObject> &Params, FSocket *ClientSocket)
{
    UWorld *World = GEditor->GetEditorWorldContext().World();

    FString Type;
    if (!Params->TryGetStringField(FStringView(TEXT("type")), Type))
    {
        MCP_LOG_WARNING("Missing 'type' field in create_object command");
        return CreateErrorResponse("Missing 'type' field");
    }

    // Get location
    const TArray<TSharedPtr<FJsonValue>> *LocationArrayPtr = nullptr;
    if (!Params->TryGetArrayField(FStringView(TEXT("location")), LocationArrayPtr) || !LocationArrayPtr || LocationArrayPtr->Num() != 3)
    {
        MCP_LOG_WARNING("Invalid 'location' field in create_object command");
        return CreateErrorResponse("Invalid 'location' field");
    }

    FVector Location(
        (*LocationArrayPtr)[0]->AsNumber(),
        (*LocationArrayPtr)[1]->AsNumber(),
        (*LocationArrayPtr)[2]->AsNumber());

    // Convert type to lowercase for case-insensitive comparison
    FString TypeLower = Type.ToLower();

    if (Type == "StaticMeshActor")
    {
        // Get mesh path if specified
        FString MeshPath;
        Params->TryGetStringField(FStringView(TEXT("mesh")), MeshPath);

        // Get label if specified
        FString Label;
        Params->TryGetStringField(FStringView(TEXT("label")), Label);

        // Create the actor
        TPair<AStaticMeshActor *, bool> Result = CreateStaticMeshActor(World, Location, MeshPath, Label);

        if (Result.Value)
        {
            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetStringField("name", Result.Key->GetName());
            ResultObj->SetStringField("label", Result.Key->GetActorLabel());
            return CreateSuccessResponse(ResultObj);
        }
        else
        {
            return CreateErrorResponse("Failed to create StaticMeshActor");
        }
    }
    else if (TypeLower == "cube")
    {
        // Create a cube actor
        FString Label;
        Params->TryGetStringField(FStringView(TEXT("label")), Label);
        TPair<AStaticMeshActor *, bool> Result = CreateCubeActor(World, Location, Label);

        if (Result.Value)
        {
            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetStringField("name", Result.Key->GetName());
            ResultObj->SetStringField("label", Result.Key->GetActorLabel());
            return CreateSuccessResponse(ResultObj);
        }
        else
        {
            return CreateErrorResponse("Failed to create cube");
        }
    }
    else
    {
        MCP_LOG_WARNING("Unsupported actor type: %s", *Type);
        return CreateErrorResponse(FString::Printf(TEXT("Unsupported actor type: %s"), *Type));
    }
}

TPair<AStaticMeshActor *, bool> FMCPCreateObjectHandler::CreateStaticMeshActor(UWorld *World, const FVector &Location, const FString &MeshPath, const FString &Label)
{
    if (!World)
    {
        return TPair<AStaticMeshActor *, bool>(nullptr, false);
    }

    // Create the actor
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = NAME_None; // Auto-generate a name
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;

    AStaticMeshActor *NewActor = World->SpawnActor<AStaticMeshActor>(Location, FRotator::ZeroRotator, SpawnParams);
    if (NewActor)
    {
        MCP_LOG_INFO("Created StaticMeshActor at location (%f, %f, %f)", Location.X, Location.Y, Location.Z);

        // Set mesh if specified
        if (!MeshPath.IsEmpty())
        {
            UStaticMesh *Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
            if (Mesh)
            {
                NewActor->GetStaticMeshComponent()->SetStaticMesh(Mesh);
                MCP_LOG_INFO("Set mesh to %s", *MeshPath);
            }
            else
            {
                MCP_LOG_WARNING("Failed to load mesh %s", *MeshPath);
            }
        }

        // Set a descriptive label
        if (!Label.IsEmpty())
        {
            NewActor->SetActorLabel(Label);
            MCP_LOG_INFO("Set custom label to %s", *Label);
        }
        else
        {
            NewActor->SetActorLabel(FString::Printf(TEXT("MCP_StaticMesh_%d"), FMath::RandRange(1000, 9999)));
        }

        return TPair<AStaticMeshActor *, bool>(NewActor, true);
    }
    else
    {
        MCP_LOG_ERROR("Failed to create StaticMeshActor");
        return TPair<AStaticMeshActor *, bool>(nullptr, false);
    }
}

TPair<AStaticMeshActor *, bool> FMCPCreateObjectHandler::CreateCubeActor(UWorld *World, const FVector &Location, const FString &Label)
{
    if (!World)
    {
        return TPair<AStaticMeshActor *, bool>(nullptr, false);
    }

    // Create a StaticMeshActor with a cube mesh
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = NAME_None;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;

    AStaticMeshActor *NewActor = World->SpawnActor<AStaticMeshActor>(Location, FRotator::ZeroRotator, SpawnParams);
    if (NewActor)
    {
        MCP_LOG_INFO("Created Cube at location (%f, %f, %f)", Location.X, Location.Y, Location.Z);

        // Set cube mesh
        UStaticMesh *CubeMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
        if (CubeMesh)
        {
            NewActor->GetStaticMeshComponent()->SetStaticMesh(CubeMesh);
            MCP_LOG_INFO("Set cube mesh");

            // Set a descriptive label
            if (!Label.IsEmpty())
            {
                NewActor->SetActorLabel(Label);
                MCP_LOG_INFO("Set custom label to %s", *Label);
            }
            else
            {
                NewActor->SetActorLabel(FString::Printf(TEXT("MCP_Cube_%d"), FMath::RandRange(1000, 9999)));
            }

            return TPair<AStaticMeshActor *, bool>(NewActor, true);
        }
        else
        {
            MCP_LOG_WARNING("Failed to load cube mesh");
            World->DestroyActor(NewActor);
            return TPair<AStaticMeshActor *, bool>(nullptr, false);
        }
    }
    else
    {
        MCP_LOG_ERROR("Failed to create Cube");
        return TPair<AStaticMeshActor *, bool>(nullptr, false);
    }
}

//
// FMCPModifyObjectHandler
//
TSharedPtr<FJsonObject> FMCPModifyObjectHandler::Execute(const TSharedPtr<FJsonObject> &Params, FSocket *ClientSocket)
{
    UWorld *World = GEditor->GetEditorWorldContext().World();

    FString ActorName;
    if (!Params->TryGetStringField(FStringView(TEXT("name")), ActorName))
    {
        MCP_LOG_WARNING("Missing 'name' field in modify_object command");
        return CreateErrorResponse("Missing 'name' field");
    }

    AActor *Actor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName)
        {
            Actor = *It;
            break;
        }
    }

    if (!Actor)
    {
        MCP_LOG_WARNING("Actor not found: %s", *ActorName);
        return CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    bool bModified = false;

    // Check for location update
    const TArray<TSharedPtr<FJsonValue>> *LocationArrayPtr = nullptr;
    if (Params->TryGetArrayField(FStringView(TEXT("location")), LocationArrayPtr) && LocationArrayPtr && LocationArrayPtr->Num() == 3)
    {
        FVector NewLocation(
            (*LocationArrayPtr)[0]->AsNumber(),
            (*LocationArrayPtr)[1]->AsNumber(),
            (*LocationArrayPtr)[2]->AsNumber());

        Actor->SetActorLocation(NewLocation);
        MCP_LOG_INFO("Updated location of %s to (%f, %f, %f)", *ActorName, NewLocation.X, NewLocation.Y, NewLocation.Z);
        bModified = true;
    }

    // Check for rotation update
    const TArray<TSharedPtr<FJsonValue>> *RotationArrayPtr = nullptr;
    if (Params->TryGetArrayField(FStringView(TEXT("rotation")), RotationArrayPtr) && RotationArrayPtr && RotationArrayPtr->Num() == 3)
    {
        FRotator NewRotation(
            (*RotationArrayPtr)[0]->AsNumber(),
            (*RotationArrayPtr)[1]->AsNumber(),
            (*RotationArrayPtr)[2]->AsNumber());

        Actor->SetActorRotation(NewRotation);
        MCP_LOG_INFO("Updated rotation of %s to (%f, %f, %f)", *ActorName, NewRotation.Pitch, NewRotation.Yaw, NewRotation.Roll);
        bModified = true;
    }

    // Check for scale update
    const TArray<TSharedPtr<FJsonValue>> *ScaleArrayPtr = nullptr;
    if (Params->TryGetArrayField(FStringView(TEXT("scale")), ScaleArrayPtr) && ScaleArrayPtr && ScaleArrayPtr->Num() == 3)
    {
        FVector NewScale(
            (*ScaleArrayPtr)[0]->AsNumber(),
            (*ScaleArrayPtr)[1]->AsNumber(),
            (*ScaleArrayPtr)[2]->AsNumber());

        Actor->SetActorScale3D(NewScale);
        MCP_LOG_INFO("Updated scale of %s to (%f, %f, %f)", *ActorName, NewScale.X, NewScale.Y, NewScale.Z);
        bModified = true;
    }

    if (bModified)
    {
        // Create a result object with the actor name
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetStringField("name", Actor->GetName());

        // Return success with the result object
        return CreateSuccessResponse(Result);
    }
    else
    {
        MCP_LOG_WARNING("No modifications specified for %s", *ActorName);
        TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();
        Response->SetStringField("status", "warning");
        Response->SetStringField("message", "No modifications specified");
        return Response;
    }
}

//
// FMCPDeleteObjectHandler
//
TSharedPtr<FJsonObject> FMCPDeleteObjectHandler::Execute(const TSharedPtr<FJsonObject> &Params, FSocket *ClientSocket)
{
    UWorld *World = GEditor->GetEditorWorldContext().World();

    FString ActorName;
    if (!Params->TryGetStringField(FStringView(TEXT("name")), ActorName))
    {
        MCP_LOG_WARNING("Missing 'name' field in delete_object command");
        return CreateErrorResponse("Missing 'name' field");
    }

    AActor *Actor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName)
        {
            Actor = *It;
            break;
        }
    }

    if (!Actor)
    {
        MCP_LOG_WARNING("Actor not found: %s", *ActorName);
        return CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Check if the actor can be deleted
    if (!FActorEditorUtils::IsABuilderBrush(Actor))
    {
        bool bDestroyed = World->DestroyActor(Actor);
        if (bDestroyed)
        {
            MCP_LOG_INFO("Deleted actor: %s", *ActorName);
            return CreateSuccessResponse();
        }
        else
        {
            MCP_LOG_ERROR("Failed to delete actor: %s", *ActorName);
            return CreateErrorResponse(FString::Printf(TEXT("Failed to delete actor: %s"), *ActorName));
        }
    }
    else
    {
        MCP_LOG_WARNING("Cannot delete special actor: %s", *ActorName);
        return CreateErrorResponse(FString::Printf(TEXT("Cannot delete special actor: %s"), *ActorName));
    }
}

//
// FMCPExecutePythonHandler
//
TSharedPtr<FJsonObject> FMCPExecutePythonHandler::Execute(const TSharedPtr<FJsonObject> &Params, FSocket *ClientSocket)
{
    FString PythonCode;
    FString PythonFile;
    bool bHasCode = Params->TryGetStringField(FStringView(TEXT("code")), PythonCode);
    bool bHasFile = Params->TryGetStringField(FStringView(TEXT("file")), PythonFile);

    if (!bHasCode && !bHasFile)
    {
        const TSharedPtr<FJsonObject>* DataObject = nullptr;
        if (Params->TryGetObjectField(FStringView(TEXT("data")), DataObject) && DataObject && DataObject->IsValid())
        {
            bHasCode = (*DataObject)->TryGetStringField(FStringView(TEXT("code")), PythonCode);
            bHasFile = (*DataObject)->TryGetStringField(FStringView(TEXT("file")), PythonFile);
        }
    }

    if (!bHasCode && !bHasFile)
    {
        MCP_LOG_WARNING("Missing 'code' or 'file' field in execute_python command");
        return CreateErrorResponse("Missing 'code' or 'file' field. Provide literal Python code or a Python file path.");
    }

    IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();
    if (!PythonPlugin)
    {
        return CreateErrorResponse("PythonScriptPlugin module is not available.");
    }
    if (!PythonPlugin->IsPythonAvailable())
    {
        return CreateErrorResponse("Python support is not available in this Unreal Editor session.");
    }
    if (!PythonPlugin->IsPythonInitialized())
    {
        return CreateErrorResponse("Python is configured but has not finished initializing.");
    }

    FPythonCommandEx Command;
    Command.Command = bHasCode ? PythonCode : PythonFile;
    Command.ExecutionMode = EPythonCommandExecutionMode::ExecuteFile;
    Command.FileExecutionScope = EPythonFileExecutionScope::Private;

    MCP_LOG_INFO("Executing Python through IPythonScriptPlugin::ExecPythonCommandEx (%s)",
        bHasCode ? TEXT("literal code") : TEXT("file"));

    const bool bSuccess = PythonPlugin->ExecPythonCommandEx(Command);

    FString CapturedOutput;
    for (const FPythonLogOutputEntry& Entry : Command.LogOutput)
    {
        FString Line = Entry.Output;
        if (!Line.EndsWith(TEXT("\n")))
        {
            Line += TEXT("\n");
        }
        CapturedOutput += Line;
    }

    CapturedOutput.TrimEndInline();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField("output", CapturedOutput);
    ResultObj->SetStringField("command_result", Command.CommandResult);

    if (bSuccess)
    {
        MCP_LOG_INFO("Python execution successful");
        return CreateSuccessResponse(ResultObj);
    }

    FString ErrorMessage = !Command.CommandResult.IsEmpty() ? Command.CommandResult : CapturedOutput;
    if (ErrorMessage.IsEmpty())
    {
        ErrorMessage = TEXT("Python execution failed. Check Unreal's Python/output log for details.");
    }

    MCP_LOG_ERROR("Python execution failed: %s", *ErrorMessage);
    ResultObj->SetStringField("error", ErrorMessage);

    TSharedPtr<FJsonObject> Response = MakeShared<FJsonObject>();
    Response->SetStringField("status", "error");
    Response->SetStringField("message", "Python execution failed");
    Response->SetObjectField("result", ResultObj);
    return Response;
}
