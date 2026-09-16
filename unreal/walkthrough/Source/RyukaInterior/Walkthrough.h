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
 void Finish1(); void Finish2(); void Finish3(); void SunLow(); void SunHigh(); void ToggleRoomLights();
 void NextPreviewHour(); void NextPreviewSeason();
 void SaveView(); void RestoreView(); void ToggleMouse(); void InteractDoor();
 FString CurrentVariantLabel() const;
 FString CurrentSolarLabel() const;
 FString CurrentLightingLabel() const;
 FString CurrentRoomLabel() const;
 FString DoorPromptLabel() const;
 bool DoorFocusPoint(FVector& WorldPoint) const;
 bool CanToggleFocusedDoor() const {return bNearestDoorCanToggle;}
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
 struct FLeafInfo {FString Actor; FString Kind; bool bHasYaw=false; double OpenYawDeltaDeg=0; bool bHasOffset=false; FVector OpenOffsetCm=FVector::ZeroVector; bool bBakedOpen=false; bool bHasClosedLocation=false; FVector ClosedLocationCm=FVector::ZeroVector;};
 struct FConnectionInfo {FString Id; TArray<FString> RoomIds; FString Operation; bool bOpenable=false; bool bHorizontal=false; double AtCm=0; double LoCm=0; double HiCm=0; TArray<FLeafInfo> Leaves; FString Label; bool bDiagonal=false; FVector2D A,B;};
 struct FOpeningWindow {bool bDiagonal=false; FVector2D A,B; bool bHorizontal=false; double At=0; double Lo=0; double Hi=0;};
 struct FStairStep {TArray<FVector2D> Polygon; double TopCm=0; FString RoomId;};
 TArray<FStairStep> StairSteps;
 FString StairRoomAt(const FVector& P) const;
 TMap<FString,FRoomInfo> Rooms;
 TArray<FConnectionInfo> Connections;
 TMap<FString,TArray<FOpeningWindow>> RoomOpenings;
 TArray<FString> EditRoomIds;
 FString ProfileId, EntryRoomId, CurrentRoomId, NearestDoorId;
 bool bNearestDoorCanToggle=false;
 float DoorFocusCheckRemaining=0.f;
 mutable bool bDoorActorsCached=false;
 mutable TMap<FString,TWeakObjectPtr<AActor>> DoorActorCache;
 // W07-G2 review-v2 R1: a slide leaf's CLOSED world location is no longer
 // guessed at runtime from a live actor pose (an editor .umap save, an Undo
 // or a reload could persist the leaf OPEN and be mistaken for closed).
 // import_study.py captures it once on the fresh imported scene and stamps
 // FLeafInfo::ClosedLocationCm into door-bindings.json -> walkthrough.json;
 // ApplyConditions() reads that fixed value directly.
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
 // 2026-09-16: data/visual/lighting-settings.json as copied into the project.
 // Only `nightExposureEV100` is read here (ApplyConditions(): fixed exposure
 // for night mode instead of the state's daytime exposureEV100 -- see
 // unreal/lighting.py night_exposure_ev100(), the editor-side twin). Absent
 // (pre-2026-09-16 project) means night keeps using the day value as before.
 TSharedPtr<class FJsonObject> LightingSettings;
 TSharedPtr<class FJsonObject> TimePresets;
 FVector LastSafeLocation=FVector::ZeroVector;
 mutable FString LastLeafMotionBlocker;  // W07-G2: diagnostic -- label of whatever last limited/blocked a leaf's motion
 void SetFinish(const FString& Name,const FString& Label);
 void SetSun(float Elevation);
 void CyclePreviewTime(bool bSeason);
 bool ApplyConditions();
 bool IsCurrentRoomEditable() const;
 bool InsideRoomPolygon(const FString& RoomId, const FVector& Position, bool bStrict) const;
 bool SafeDuringMovement(const FVector& Position) const;
 bool Safe(const FVector& Position) const;
 bool Safe(const FVector& Position, const FString& RoomId) const;
 void UpdateCurrentRoom();
 // 2026-09-14追加：人感ダウンライト（light-downlight-sensor、
 // data/electrical-catalog.json）の自動点灯。lighting-bindings.jsonの
 // fixture.type（W06のbuild_lighting_bindings()が常に含めている）でこの
 // 型の器具だけを対象に、`RoomId`内で既にonのものは変更せず、offのものだけ
 // ToggleRoomLights()と同じ「roomStates[room].fixtures[id].onを書き換えて
 // ApplyConditions()を通す」経路で点灯させる。IsCurrentRoomEditable()（仕
 // 上げ編集対象＝LDK・洋室のみ）とは無関係に、対象範囲内のどの部屋でも動く
 // （ToggleRoomLights()のLキー操作が既にそうであるのと同じ扱い）。自動消灯
 // は施主指示（2026-09-14「入ったら自動で点く」）の範囲外のため未実装。
 void ApplySensorLights(const FString& RoomId);
 void FindNearestDoor();
 bool CheckFocusedDoorMotion() const;
 TMap<FString,AActor*> FindDoorActors(const FConnectionInfo& Connection) const;
 FTransform DoorLeafTargetTransform(const FLeafInfo& Leaf,AActor* LeafActor,bool bOpen) const;
 bool GetDoorOpen(const FString& DoorId) const;
 // W07-G2 review-v3 R3: fraction [0,1] of the From->To leaf motion that is
 // clear. 1.0 == the whole motion is clear. Both end poses are already
 // generation-validated against the fixed building walls (see
 // circulation.py's maxSwingDeltaDeg), so this watches only for FURNITURE,
 // another door's leaf, and -- when `bCheckPlayer` (an interactive toggle)
 // -- the player's own capsule between the two poses. Always excluded: the
 // leaf, this door's own frame + sibling leaves (AlsoIgnore), every door's
 // frame pieces (jambs/head/sill), and the building walls (wall_/Ground_).
 float LeafMotionClearFraction(AActor* Leaf, const FTransform& From, const FTransform& To, const TArray<AActor*>& AlsoIgnore, bool bCheckPlayer) const;
 bool bInteractiveDoorToggle=false; // true only while InteractDoor()'s own ApplyConditions() runs
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
