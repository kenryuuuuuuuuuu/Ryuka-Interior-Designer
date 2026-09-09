#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Walkthrough.generated.h"

UCLASS()
class RYUKAINTERIOR_API AWalkthroughCharacter : public ACharacter {
 GENERATED_BODY()
public:
 AWalkthroughCharacter();
 virtual void BeginPlay() override;
 virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
 virtual void Tick(float Delta) override;
 void Finish1(); void Finish2(); void Finish3(); void SunLow(); void SunHigh();
 void SaveView(); void RestoreView(); void ToggleMouse(); void InteractDoor();
 FString CurrentVariantLabel() const;
 FString CurrentSolarLabel() const;
 FString CurrentLightingLabel() const;
 FString CurrentRoomLabel() const;
 FString DoorPromptLabel() const;
 FString Message;
 bool bReady=false;
 bool bInitialized=false;
 bool bSmokeDone=false;
private:
 UPROPERTY() class UCameraComponent* Eye;
 TSharedPtr<class FJsonObject> State;
 // W07-G2: multi-room replaces the single Room/Floor/WalkableRoomId a G1
 // walkthrough had. Rooms/Connections/RoomOpenings are loaded once in
 // BeginPlay() from walkthrough.json (never re-derived at runtime -- the
 // same profile/connectivity resolution Python already did once at
 // generation time, see unreal/circulation.py); a single-room, zero-door
 // profile (the pre-G2 guest-ldk-solo profile) degenerates this to exactly
 // the old single-room behaviour, not a separate code path.
 struct FRoomInfo {TArray<FVector2D> Polygon; double FloorCm=0; int32 Level=0; FString Label;};
 struct FLeafInfo {FString Actor; FString Kind; bool bHasYaw=false; double OpenYawDeltaDeg=0; bool bHasOffset=false; FVector OpenOffsetCm=FVector::ZeroVector;};
 struct FConnectionInfo {FString Id; TArray<FString> RoomIds; FString Operation; bool bOpenable=false; bool bHorizontal=false; double AtCm=0; double LoCm=0; double HiCm=0; TArray<FLeafInfo> Leaves; FString Label;};
 struct FOpeningWindow {bool bHorizontal=false; double At=0; double Lo=0; double Hi=0;};
 TMap<FString,FRoomInfo> Rooms;
 TArray<FConnectionInfo> Connections;
 TMap<FString,TArray<FOpeningWindow>> RoomOpenings;
 TArray<FString> EditRoomIds;
 FString ProfileId, EntryRoomId, CurrentRoomId, NearestDoorId;
 // A slide leaf's CLOSED world location, captured lazily the first time
 // ApplyConditions() sees it (never re-captured afterward, or repeated
 // opens/closes would drift) -- an unattached actor's "relative" location
 // API is just its absolute one, so the open offset must be added to a
 // remembered baseline rather than composed some other way.
 TMap<FString,FVector> DoorLeafSpawnLocation;
 // W04: loaded once in BeginPlay(); invalid/empty for a pre-W04 generated
 // project (no surface-bindings.json/no registered surfaces there), in
 // which case ApplyConditions() simply has no per-surface overrides to
 // apply -- not an error.
 TSharedPtr<class FJsonObject> SurfaceBindings;
 TSharedPtr<class FJsonObject> FinishDocument;
 TSharedPtr<class FJsonObject> StudyVariants;
 // W06: loaded once in BeginPlay(); invalid/empty for a pre-W06 generated
 // project (no lighting-bindings.json there), in which case ApplyConditions()
 // below just finds no fixtures to apply -- not an error.
 TSharedPtr<class FJsonObject> LightingBindings;
 FVector LastSafeLocation=FVector::ZeroVector;
 void SetFinish(const FString& Name,const FString& Label);
 void SetSun(float Elevation);
 bool ApplyConditions();
 bool IsCurrentRoomEditable() const;
 bool InsideRoomPolygon(const FString& RoomId, const FVector& Position, bool bStrict) const;
 bool Safe(const FVector& Position) const;
 bool Safe(const FVector& Position, const FString& RoomId) const;
 void UpdateCurrentRoom();
 void FindNearestDoor();
 bool GetDoorOpen(const FString& DoorId) const;
 bool Restore(const TSharedPtr<FJsonObject>& Candidate);
};

UCLASS()
class RYUKAINTERIOR_API AWalkthroughHUD : public AHUD {
 GENERATED_BODY()
public: virtual void DrawHUD() override;
};

UCLASS()
class RYUKAINTERIOR_API AWalkthroughGameMode : public AGameModeBase {
 GENERATED_BODY()
public: AWalkthroughGameMode();
};

UCLASS()
class RYUKAINTERIOR_API UWalkthroughLibrary : public UBlueprintFunctionLibrary {
 GENERATED_BODY()
public:
 UFUNCTION(BlueprintCallable) static int32 Prepare(UWorld* World);
};
