#include "Walkthrough.h"
#include "Modules/ModuleManager.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "PhysicsEngine/BodySetup.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UnrealClient.h"
#include "HAL/PlatformMisc.h"
IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl,RyukaInterior,"RyukaInterior");

static FString SavedViewName() {
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaSmoke"))) return TEXT("Saved/walkthrough-smoke-state.json");
#if !UE_BUILD_SHIPPING
 // The native fault-injection/regression tests below (-RyukaFaultSave,
 // -RyukaVerifyRecovery, -RyukaBoundaryFaultTest) call the real SaveView()/
 // RestoreView() -- deliberately, so the exact production code path is what
 // gets exercised -- but must never read, write, or delete the player's
 // actual Saved/walkthrough-state.json or its .bak. Routing all three (and
 // only these three; RyukaSmoke keeps its own separate name above) through
 // one shared test-only name here, at the single place SaveView()/
 // RestoreView() ask "which file", is what makes that guarantee hold without
 // duplicating either function.
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaFaultSave"))||FParse::Param(FCommandLine::Get(),TEXT("RyukaVerifyRecovery"))||FParse::Param(FCommandLine::Get(),TEXT("RyukaBoundaryFaultTest")))
  return TEXT("Saved/walkthrough-test-state.json");
#endif
 return TEXT("Saved/walkthrough-state.json");
}
static TSharedPtr<FJsonObject> ReadJSON(const FString& Name) {
 FString Text; TSharedPtr<FJsonObject> Value;
 if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectDir()/Name)))
  FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Value);
 return Value;
}
static TArray<TSharedPtr<FJsonValue>> Numbers(const FVector& V) {
 return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};
}
static bool VectorField(const TSharedPtr<FJsonObject>& O,const FString& Key,FVector& V) {
 const TArray<TSharedPtr<FJsonValue>>* A;
 if(!O.IsValid()||!O->TryGetArrayField(Key,A)||A->Num()!=3) return false;
 double X,Y,Z;
 if(!(*A)[0]->TryGetNumber(X)||!(*A)[1]->TryGetNumber(Y)||!(*A)[2]->TryGetNumber(Z)) return false;
 V=FVector(X,Y,Z); return !V.ContainsNaN();
}
static void SavedViewPaths(FString& Path,FString& Backup) {
 Path=FPaths::ProjectDir()/SavedViewName(); Backup=Path+TEXT(".bak");
}
// The one persistent, disk-visible signature of an incomplete SaveView(): the
// previous save was renamed aside to Backup and never made it back to Path
// (the final replace failed, and restoring Backup back to Path also failed).
// This is read purely from what is actually on disk, not cached in-memory
// state, so the same check recognizes it identically whether it is the same
// run, a later F5, or a fresh process after a restart. Returns true when
// there is nothing to recover, or recovery itself just succeeded; only when
// recovery fails does it return false, leaving Backup untouched and OutMessage
// explaining that a human needs to look at it.
static bool RecoverSaveIfNeeded(FString& OutMessage) {
 FString Path,Backup; SavedViewPaths(Path,Backup);
 if(IFileManager::Get().FileExists(*Path)||!IFileManager::Get().FileExists(*Backup)) return true;
 if(IFileManager::Get().Move(*Path,*Backup,true,true)) return true; // auto-recovered
 // Project-relative name (always plain ASCII), not FPaths::ProjectDir()'s
 // absolute path: this project's directory name is not itself ASCII, and
 // embedding the absolute path here was observed to come out corrupted in
 // this on-screen Message (FPaths::ProjectDir() round-trips correctly for
 // real file I/O -- confirmed by every save/restore in this fix actually
 // working -- but not through JSON/log serialization of that particular
 // string on this system). The relative name is also more readable on HUD.
 OutMessage=TEXT("前回の保存の復旧が必要です。バックアップ「")+SavedViewName()+TEXT(".bak」を確認してください。復旧するまで保存できません。");
 return false;
}
AWalkthroughCharacter::AWalkthroughCharacter() {
 PrimaryActorTick.bCanEverTick=true;
 GetCapsuleComponent()->InitCapsuleSize(25,88);
 Eye=CreateDefaultSubobject<UCameraComponent>(TEXT("Eye")); Eye->SetupAttachment(GetCapsuleComponent());
 Eye->SetRelativeLocation(FVector(0,0,72)); Eye->bUsePawnControlRotation=true; Eye->FieldOfView=80;
 GetCharacterMovement()->MaxWalkSpeed=120; GetCharacterMovement()->MaxStepHeight=2;
 GetCharacterMovement()->bCanWalkOffLedges=false;
 bUseControllerRotationYaw=true;
}
bool AWalkthroughCharacter::InsideRoomPolygon(const FString& RoomId,const FVector& P,bool bStrict) const {
 // Interior and (unless bStrict) 25cm clearance from the room boundary;
 // handles concave outlines. This is the invisible boundary (openings/
 // doorways have no physical wall of their own), kept separate from
 // furniture/wall collision so Tick() can enforce it after the normal
 // CharacterMovement sweep instead of blocking movement input.
 //
 // W07-G2: bStrict=true (no margin at all) is used purely for "which room
 // polygon am I actually standing in" (UpdateCurrentRoom()) -- adjacent
 // room polygons meet exactly at their shared wall line with no gap, so a
 // margin there would leave a dead zone belonging to neither room.
 // bStrict=false (the original single-room margin behaviour) is used for
 // movement safety (Safe()) and additionally relaxes the margin at this
 // room's OWN opening windows (RoomOpenings[RoomId], every door/passage
 // touching it, regardless of open/closed state) so a real connected
 // doorway is walkable right up to and through the shared edge -- a CLOSED
 // leaf's own physical collision (Prepare() gives every leaf actor complex
 // blocking collision, same as furniture) is what actually stops the
 // player there, not this soft boundary.
 const FRoomInfo* Info=Rooms.Find(RoomId); if(!Info) return false;
 const TArray<FOpeningWindow>* Openings=bStrict?nullptr:RoomOpenings.Find(RoomId);
 bool Inside=false; FVector2D Q(P.X,P.Y);
 for(int32 I=0,J=Info->Polygon.Num()-1;I<Info->Polygon.Num();J=I++) {
  const FVector2D A=Info->Polygon[I],B=Info->Polygon[J];
  if((A.Y>Q.Y)!=(B.Y>Q.Y) && Q.X<(B.X-A.X)*(Q.Y-A.Y)/(B.Y-A.Y)+A.X) Inside=!Inside;
  if(bStrict) continue;
  const FVector2D D=B-A;
  const float T=FMath::Clamp(FVector2D::DotProduct(Q-A,D)/FMath::Max(D.SizeSquared(),.001),0.,1.);
  if((Q-(A+T*D)).Size()<26) {
   bool bRelaxed=false;
   if(Openings) {
    const bool bEdgeHorizontal=FMath::Abs(A.Y-B.Y)<1.;
    const double EdgeAt=bEdgeHorizontal?A.Y:A.X, EdgeU=bEdgeHorizontal?Q.X:Q.Y;
    for(auto& W:*Openings) {
     if(W.bHorizontal!=bEdgeHorizontal) continue;
     if(FMath::Abs(EdgeAt-W.At)<1.&&EdgeU>=W.Lo-1.&&EdgeU<=W.Hi+1.) {bRelaxed=true;break;}
    }
   }
   if(!bRelaxed) return false;
  }
 }
 return Inside;
}
bool AWalkthroughCharacter::Safe(const FVector& P,const FString& RoomId) const {
 if(!InsideRoomPolygon(RoomId,P,false)) return false;
 FCollisionQueryParams Params(SCENE_QUERY_STAT(WalkthroughSpawn),false,this);
 return !GetWorld()->OverlapBlockingTestByChannel(P,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(25,87),Params);
}
bool AWalkthroughCharacter::Safe(const FVector& P) const {return Safe(P,CurrentRoomId);}
bool AWalkthroughCharacter::IsCurrentRoomEditable() const {return EditRoomIds.Contains(CurrentRoomId);}
void AWalkthroughCharacter::UpdateCurrentRoom() {
 // W07-G2: prefer staying in the CURRENT room whenever its own (strict, no
 // margin) polygon still contains the player -- this is what keeps the
 // room label/edit target stable while standing in a door's thickness
 // (spec section 3: "扉の厚み部分では直前室を維持"), since adjoining room
 // polygons share their boundary line exactly (no gap) and a point sitting
 // precisely on it belongs to the FIRST polygon tried, not neither/both.
 // Only DIRECTLY connected rooms are checked for a transition -- movement
 // is continuous and real wall collision elsewhere prevents ever reaching a
 // non-adjacent room's polygon in a single tick anyway.
 const FVector P=GetActorLocation();
 if(InsideRoomPolygon(CurrentRoomId,P,true)) return;
 for(auto& Connection:Connections) {
  if(!Connection.RoomIds.Contains(CurrentRoomId)) continue;
  for(auto& OtherRoomId:Connection.RoomIds) {
   if(OtherRoomId==CurrentRoomId) continue;
   if(InsideRoomPolygon(OtherRoomId,P,true)) {
    CurrentRoomId=OtherRoomId;
    // W07-G2 spec section 3: "編集scope内に入ればその室を編集対象へ同期"
    // -- entering an edit-scope room while ready syncs activeRoomId so the
    // finish keys affect THIS room; leaving it (into e.g. the hall) leaves
    // activeRoomId (and therefore the LDK/western-room finish) untouched,
    // never guessed at from a non-edit room.
    if(bReady&&State.IsValid()&&IsCurrentRoomEditable()) State->SetStringField(TEXT("activeRoomId"),CurrentRoomId);
    return;
   }
  }
 }
}
void AWalkthroughCharacter::FindNearestDoor() {
 NearestDoorId.Empty();
 if(!bReady) return;
 const FVector EyeLoc=Eye->GetComponentLocation(); const FVector Forward=Eye->GetForwardVector();
 double Best=250.; // cm interaction range -- close enough to actually touch the door, never through a wall
 for(auto& C:Connections) {
  if(!C.bOpenable||!C.RoomIds.Contains(CurrentRoomId)) continue;
  const double MidU=(C.LoCm+C.HiCm)/2.;
  const FVector DoorPos=C.bHorizontal?FVector(MidU,C.AtCm,EyeLoc.Z):FVector(C.AtCm,MidU,EyeLoc.Z);
  const FVector ToDoor=DoorPos-EyeLoc; const double Dist=ToDoor.Size();
  if(Dist>Best) continue;
  if(FVector::DotProduct(Forward,ToDoor.GetSafeNormal())<0.5) continue; // roughly facing it, not just nearby
  Best=Dist; NearestDoorId=C.Id;
 }
}
bool AWalkthroughCharacter::GetDoorOpen(const FString& DoorId) const {
 if(!State.IsValid()) return false;
 const TSharedPtr<FJsonObject>* DoorStatesObj;
 if(!State->TryGetObjectField(TEXT("doorStates"),DoorStatesObj)) return false;
 const TSharedPtr<FJsonObject>* Override;
 if(!(*DoorStatesObj)->TryGetObjectField(DoorId,Override)) return false;
 bool bOpen=false; (*Override)->TryGetBoolField(TEXT("open"),bOpen); return bOpen;
}
FString AWalkthroughCharacter::CurrentRoomLabel() const {
 if(const FRoomInfo* Info=Rooms.Find(CurrentRoomId)) return Info->Label.IsEmpty()?CurrentRoomId:Info->Label;
 return CurrentRoomId;
}
FString AWalkthroughCharacter::DoorPromptLabel() const {
 if(NearestDoorId.IsEmpty()) return FString();
 for(auto& C:Connections) if(C.Id==NearestDoorId)
  return (GetDoorOpen(C.Id)?TEXT("[E] 閉じる："):TEXT("[E] 開ける："))+(C.Label.IsEmpty()?C.Id:C.Label);
 return FString();
}
void AWalkthroughCharacter::BeginPlay() {
 Super::BeginPlay();
 auto Config=ReadJSON(TEXT("walkthrough.json"));
 if(!Config.IsValid()) {Message=TEXT("内覧の設定が見つかりません"); GetCharacterMovement()->DisableMovement(); return;}
 // W07-G2: multi-room replaces the single roomId/floorCm/polygonCm a G1
 // walkthrough.json had -- rooms/connections come from
 // unreal/circulation.py's own connectivity resolution, run once at
 // generation time (scripts/enable-unreal-walkthrough.py), never re-derived
 // here. A single-room, zero-connection profile (pre-G2's guest-ldk-solo)
 // degenerates every multi-room code path below to exactly the old
 // single-room behaviour.
 Config->TryGetStringField(TEXT("profileId"),ProfileId);
 Config->TryGetStringField(TEXT("entryRoomId"),EntryRoomId);
 CurrentRoomId=EntryRoomId;
 const TArray<TSharedPtr<FJsonValue>>* EditRoomIdsArray;
 if(Config->TryGetArrayField(TEXT("editRoomIds"),EditRoomIdsArray))
  for(auto& V:*EditRoomIdsArray) EditRoomIds.Add(V->AsString());
 const TSharedPtr<FJsonObject>* RoomsObj;
 if(Config->TryGetObjectField(TEXT("rooms"),RoomsObj)) {
  for(auto& Entry:(*RoomsObj)->Values) {
   auto RoomObj=Entry.Value->AsObject(); if(!RoomObj.IsValid()) continue;
   FRoomInfo Info;
   RoomObj->TryGetNumberField(TEXT("floorCm"),Info.FloorCm);
   int32 Level=1; RoomObj->TryGetNumberField(TEXT("level"),Level); Info.Level=Level;
   RoomObj->TryGetStringField(TEXT("label"),Info.Label);
   const TArray<TSharedPtr<FJsonValue>>* PolygonArray;
   if(RoomObj->TryGetArrayField(TEXT("polygonCm"),PolygonArray))
    for(auto& V:*PolygonArray) {auto A=V->AsArray(); Info.Polygon.Add(FVector2D(A[0]->AsNumber(),A[1]->AsNumber()));}
   Rooms.Add(FString(*Entry.Key),Info);
  }
 }
 const TArray<TSharedPtr<FJsonValue>>* ConnectionsArray;
 if(Config->TryGetArrayField(TEXT("connections"),ConnectionsArray)) {
  for(auto& CV:*ConnectionsArray) {
   auto CObj=CV->AsObject(); if(!CObj.IsValid()) continue;
   FConnectionInfo Info;
   CObj->TryGetStringField(TEXT("id"),Info.Id);
   const TArray<TSharedPtr<FJsonValue>>* RoomIdsArray;
   if(CObj->TryGetArrayField(TEXT("roomIds"),RoomIdsArray)) for(auto& V:*RoomIdsArray) Info.RoomIds.Add(V->AsString());
   CObj->TryGetStringField(TEXT("operation"),Info.Operation);
   CObj->TryGetBoolField(TEXT("openable"),Info.bOpenable);
   FString Orientation; CObj->TryGetStringField(TEXT("orientation"),Orientation); Info.bHorizontal=(Orientation==TEXT("H"));
   CObj->TryGetNumberField(TEXT("atCm"),Info.AtCm); CObj->TryGetNumberField(TEXT("loCm"),Info.LoCm); CObj->TryGetNumberField(TEXT("hiCm"),Info.HiCm);
   CObj->TryGetStringField(TEXT("label"),Info.Label);
   const TArray<TSharedPtr<FJsonValue>>* LeavesArray;
   if(CObj->TryGetArrayField(TEXT("leaves"),LeavesArray)) {
    for(auto& LV:*LeavesArray) {
     auto LObj=LV->AsObject(); if(!LObj.IsValid()) continue;
     FLeafInfo Leaf; LObj->TryGetStringField(TEXT("actor"),Leaf.Actor); LObj->TryGetStringField(TEXT("kind"),Leaf.Kind);
     double Yaw; if(LObj->TryGetNumberField(TEXT("openYawDeltaDeg"),Yaw)) {Leaf.bHasYaw=true; Leaf.OpenYawDeltaDeg=Yaw;}
     const TArray<TSharedPtr<FJsonValue>>* OffsetArray;
     if(LObj->TryGetArrayField(TEXT("openOffsetCm"),OffsetArray)&&OffsetArray->Num()==3) {
      Leaf.bHasOffset=true;
      Leaf.OpenOffsetCm=FVector((*OffsetArray)[0]->AsNumber(),(*OffsetArray)[1]->AsNumber(),(*OffsetArray)[2]->AsNumber());
     }
     Info.Leaves.Add(Leaf);
    }
   }
   Connections.Add(Info);
  }
 }
 // Every room's own opening windows, from every connection touching it,
 // regardless of open/closed state -- see InsideRoomPolygon()'s own comment
 // for why this relaxation does not need to be conditional on door state.
 for(auto& C:Connections) for(auto& RoomId:C.RoomIds) {
  FOpeningWindow W; W.bHorizontal=C.bHorizontal; W.At=C.AtCm; W.Lo=C.LoCm; W.Hi=C.HiCm;
  RoomOpenings.FindOrAdd(RoomId).Add(W);
 }
 // W04: optional -- absent for a project generated before this feature, in
 // which case ApplyConditions() below just finds nothing to apply per-surface.
 SurfaceBindings=ReadJSON(TEXT("surface-bindings.json"));
 FinishDocument=ReadJSON(TEXT("finish-settings.json"));
 LightingBindings=ReadJSON(TEXT("lighting-bindings.json"));
 if(auto Study=ReadJSON(TEXT("SourcePackage/study.json"))) {
  const TSharedPtr<FJsonObject>* SettingsObj;
  if(Study->TryGetObjectField(TEXT("settings"),SettingsObj)) {
   const TSharedPtr<FJsonObject>* VariantsObj;
   if((*SettingsObj)->TryGetObjectField(TEXT("variants"),VariantsObj)) StudyVariants=*VariantsObj;
  }
 }
 GetCharacterMovement()->DisableMovement();
}
bool AWalkthroughCharacter::Restore(const TSharedPtr<FJsonObject>& Candidate) {
 FString Schema;
 // W07-G2: only schemaVersion 2.1.0 is ever handed to Restore() now --
 // study_controls.py/every CLI path always migrates a legacy save in-memory
 // before it reaches a UE project's study-state.json at all (see
 // unreal/multi_room_state.py), so a RUNTIME save (F5/SaveView()) is always
 // 2.1.0-shaped too.
 if(!Candidate.IsValid()||!Candidate->TryGetStringField(TEXT("schemaVersion"),Schema)||Schema!=TEXT("2.1.0")) {
  Message=TEXT("保存データの形式（バージョン）が無効です"); return false;
 }
 const TSharedPtr<FJsonObject>* CandidateRoomStates;
 if(!Candidate->TryGetObjectField(TEXT("roomStates"),CandidateRoomStates)) {
  Message=TEXT("保存データの部屋情報が無効です"); return false;
 }
 // W07-G2: roomStates now covers the EDIT scope (LDK+洋室), not necessarily
 // whatever room the player is walking in (a non-edit room like the hall has
 // no roomState at all) -- "this is MY project's save" is checked against
 // the edit scope instead of a single walkable room.
 for(auto& RoomId:EditRoomIds) if(!(*CandidateRoomStates)->HasField(RoomId)) {
  Message=TEXT("別のプロジェクトの保存データです"); return false;
 }
 const TSharedPtr<FJsonObject>* Camera; FVector P,R; double LensMm;
 if(!Candidate->TryGetObjectField(TEXT("camera"),Camera)||!VectorField(*Camera,TEXT("locationCm"),P)||!VectorField(*Camera,TEXT("rotationDeg"),R)) {
  Message=TEXT("保存データのカメラ情報が無効です"); return false;
 }
 // Inverse of the 36mm-sensor convention used by SaveView()/study_state.py:
 // lensMm=18/tan(FOV/2) -> FOV=2*atan(18/lensMm). Range matches study_state.py.
 if(!(*Camera)->TryGetNumberField(TEXT("lensMm"),LensMm)||!FMath::IsFinite(LensMm)||LensMm<12.||LensMm>120.) {
  Message=TEXT("保存データの画角が無効です"); return false;
 }
 // W07-G2 spec section 4: "自己申告room/levelを信じず現在モデルで検証" --
 // walkthrough.roomId only wins if it actually names a room this profile
 // still has; otherwise (never launched, an edited-out room, a foreign
 // save) fall back to the profile's own entry room.
 FString TargetRoomId=EntryRoomId;
 const TSharedPtr<FJsonObject>* WalkthroughObj;
 if(Candidate->TryGetObjectField(TEXT("walkthrough"),WalkthroughObj)&&WalkthroughObj->IsValid()) {
  FString CandidateRoomId;
  if((*WalkthroughObj)->TryGetStringField(TEXT("roomId"),CandidateRoomId)&&Rooms.Contains(CandidateRoomId)) TargetRoomId=CandidateRoomId;
 }
 const FRoomInfo* TargetRoom=Rooms.Find(TargetRoomId);
 if(!TargetRoom) {Message=TEXT("対象室が見つかりません"); return false;}
 auto Previous=State; const FString PreviousRoomId=CurrentRoomId;
 // W07-G2 spec section 4: "F9は候補の扉状態で安全性を評価してから適用" --
 // State/CurrentRoomId switch to the candidate FIRST so ApplyConditions()
 // (below) actually moves every leaf to the candidate's own doorStates
 // before the safety search runs against them.
 State=Candidate; CurrentRoomId=TargetRoomId;
 if(!ApplyConditions()) {State=Previous; CurrentRoomId=PreviousRoomId; Message=TEXT("保存データの仕上げ・太陽条件を適用できません"); return false;}
 P.Z=TargetRoom->FloorCm+88.5;
 bool Adjusted=false;
 if(!Safe(P,CurrentRoomId)) {
  double Best=TNumericLimits<double>::Max(); FVector Found;
  for(int32 X=0;X<100;X++) for(int32 Y=0;Y<100;Y++) {
   FVector Test(TargetRoom->Polygon[0].X-500+X*15,TargetRoom->Polygon[0].Y-500+Y*15,P.Z);
   double Distance=FVector::DistSquared2D(P,Test);
   if(Distance<Best&&Safe(Test,CurrentRoomId)) {Best=Distance; Found=Test;}
  }
  if(Best==TNumericLimits<double>::Max()) {
   // W07-G2 spec section 4: "安全位置がなければ元のシーンと保存を維持して
   // 拒否" -- restore the previous state's own door leaf transforms too,
   // not just the in-memory State pointer, so nothing is left half-applied.
   State=Previous; CurrentRoomId=PreviousRoomId; ApplyConditions();
   Message=TEXT("安全な開始位置がありません。家具配置を確認してください。");return false;
  }
  P=Found; Adjusted=true;
 }
 SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);
 GetCharacterMovement()->StopMovementImmediately(); GetCharacterMovement()->SetMovementMode(MOVE_Walking);
 Controller->SetControlRotation(FRotator(FMath::Clamp(R.X,-80.,80.),R.Y,0));
 Eye->FieldOfView=FMath::RadiansToDegrees(2.*atan(18./LensMm));
 LastSafeLocation=P;
 bReady=true; Message=Adjusted?TEXT("空いている最も近い位置へ移動しました"):TEXT("視点を復元しました"); return true;
}
void AWalkthroughCharacter::RestoreView() {
 FString RecoveryMessage;
 if(!RecoverSaveIfNeeded(RecoveryMessage)) {
  // An unrecovered Backup means the last save's fate is unknown -- silently
  // falling back to study-state.json here would look like a normal restore
  // and could lead to it being overwritten later. Stop instead of guessing.
  Message=RecoveryMessage; bReady=false; GetCharacterMovement()->DisableMovement(); return;
 }
 const FString Saved=FPaths::ProjectDir()/SavedViewName(), Base=FPaths::ProjectDir()/TEXT("study-state.json");
 const bool Newer=IFileManager::Get().GetTimeStamp(*Saved)>IFileManager::Get().GetTimeStamp(*Base);
 if(Newer) {
  if(Restore(ReadJSON(SavedViewName()))) return;
  // Restore() already set a specific reason (invalid schema, wrong room, no
  // safe candidate, etc.); keep it so a fallback success below does not
  // silently overwrite it with a generic "view restored" message.
  const FString Reason=Message;
  if(Restore(ReadJSON(TEXT("study-state.json")))) {
   Message=TEXT("保存データが無効なため基準状態に戻しました（")+Reason+TEXT("）"); return;
  }
  // Restore() above already left Message with study-state.json's own failure
  // reason (e.g. no safe candidate); that is the more relevant one to show
  // here since it explains why nothing could be restored at all, so it is
  // not replaced with Reason from the earlier saved-file attempt.
 } else if(Restore(ReadJSON(TEXT("study-state.json")))) return;
 // Every Restore() failure path above sets a specific reason already; no
 // generic fallback message here so that reason is not silently replaced.
 bReady=false; GetCharacterMovement()->DisableMovement();
}
bool AWalkthroughCharacter::ApplyConditions() {
 static const FString BaseVariant=TEXT("natural");  // matches unreal/multi_room_state.py's BASE_VARIANT
 auto Bindings=ReadJSON(TEXT("study-bindings.json")); if(!Bindings.IsValid()||!State.IsValid()) return false;
 double Az,El,Lux,EV;
 if(!State->TryGetNumberField(TEXT("azimuthDeg"),Az)||
 !State->TryGetNumberField(TEXT("elevationDeg"),El)||!State->TryGetNumberField(TEXT("sunLux"),Lux)||!State->TryGetNumberField(TEXT("exposureEV100"),EV)) return false;
 if(!FMath::IsFinite(Az)||!FMath::IsFinite(El)||!FMath::IsFinite(Lux)||!FMath::IsFinite(EV)||Az<0||Az>360||El<1||El>89||Lux<1||Lux>150000||EV< -5||EV>20) return false;
 // W07-G2: only 2.1.0 states ever reach here (see Restore()) -- roomStates
 // (per-room variant/surfaceOverrides/fixtures) is unchanged from W07-G1;
 // doorStates/walkthrough are new (handled further below).
 FString SchemaVersion; if(!State->TryGetStringField(TEXT("schemaVersion"),SchemaVersion)||SchemaVersion!=TEXT("2.1.0")) return false;
 const TSharedPtr<FJsonObject>* RoomStatesObj;
 if(!State->TryGetObjectField(TEXT("roomStates"),RoomStatesObj)) return false;
 auto GetRoomState=[RoomStatesObj](const FString& RoomId)->const TSharedPtr<FJsonObject>* {
  const TSharedPtr<FJsonObject>* Found;
  return (*RoomStatesObj)->TryGetObjectField(RoomId,Found) ? Found : nullptr;
 };
 TMap<FString,AActor*> Actors;
 for(TActorIterator<AActor> It(GetWorld());It;++It) for(auto Tag:It->Tags) if(Tag.ToString().StartsWith(TEXT("Ryuka:"))) Actors.Add(Tag.ToString().Mid(6),*It);
 // W07-G1: study-bindings.json's whole-scene role-slot entries now each
 // carry their OWNING room (or none, for exterior/un-owned geometry) --
 // that room's OWN variant picks the material, never one single global
 // value (spec section 3: "グローバルなroleマテリアル一括置換を室所有へ").
 struct Assignment {UStaticMeshComponent* Component; int32 Slot; UMaterialInterface* Material;}; TArray<Assignment> Plan;
 for(auto& Entry:Bindings->Values) {
  auto Actor=Cast<AStaticMeshActor>(Actors.FindRef(FString(*Entry.Key))); if(!Actor) return false;
  auto EntryObj=Entry.Value->AsObject(); if(!EntryObj.IsValid()) return false;
  // Named RoleRoomId (not EntryRoomId) to avoid shadowing the class member
  // EntryRoomId (the walkthrough profile's own starting room, unrelated to
  // this per-actor role binding's owning room) -- MSVC treats the shadow as
  // error C4458 under this project's warning level.
  FString RoleRoomId; EntryObj->TryGetStringField(TEXT("roomId"),RoleRoomId);  // absent/empty = un-owned
  FString RoleVariant=BaseVariant;
  if(!RoleRoomId.IsEmpty()) {
   auto RoleRoomState=GetRoomState(RoleRoomId); if(!RoleRoomState) return false;
   if(!(*RoleRoomState)->TryGetStringField(TEXT("variant"),RoleVariant)) return false;
  }
  const TSharedPtr<FJsonObject>* SlotsObj;
  if(!EntryObj->TryGetObjectField(TEXT("slots"),SlotsObj)) return false;
  auto Component=Actor->GetStaticMeshComponent();
  for(auto& Slot:(*SlotsObj)->Values) {
   auto Material=LoadObject<UMaterialInterface>(nullptr,*(TEXT("/Game/Generated/Finishes/M_")+RoleVariant+TEXT("_")+Slot.Value->AsString()));
   int32 Index=FCString::Atoi(*Slot.Key);
   if(!Material||Index<0||Index>=Component->GetNumMaterials()) return false;
   Plan.Add({Component,Index,Material});
  }
 }
 auto Sun=Cast<ADirectionalLight>(Actors.FindRef(TEXT("Sun_manual_angle")));
 auto Post=Cast<APostProcessVolume>(Actors.FindRef(TEXT("Fixed_exposure"))); if(!Sun||!Post) return false;
 // W06/W07-G1: night lighting -- `lighting` stays whole-house (mode only,
 // per-fixture state moved to each room's OWN fixtures dict). Resolved
 // fully here (no mutation yet), same discipline as the surfaceOverrides
 // block below. FixtureOverrides is aggregated across EVERY in-scope room
 // (fixture ids are unique across rooms) so the existing per-fixture
 // lookup/"unconsumed key" logic below is otherwise unchanged.
 FString LightingMode=TEXT("day");
 TMap<FString,TSharedPtr<FJsonObject>> FixtureOverrides;
 {
  const TSharedPtr<FJsonObject>* LightingObj;
  if(!State->TryGetObjectField(TEXT("lighting"),LightingObj)) return false;
  if(!(*LightingObj)->TryGetStringField(TEXT("mode"),LightingMode)||(LightingMode!=TEXT("day")&&LightingMode!=TEXT("night"))) return false;
  for(auto& RoomEntry:(*RoomStatesObj)->Values) {
   auto RoomObj=RoomEntry.Value->AsObject(); if(!RoomObj.IsValid()) return false;
   const TSharedPtr<FJsonObject>* FixturesObj;
   if(!RoomObj->TryGetObjectField(TEXT("fixtures"),FixturesObj)) return false;
   for(auto& Entry:(*FixturesObj)->Values) {
    auto Override=Entry.Value->AsObject(); if(!Override.IsValid()) return false;
    for(auto& Field:Override->Values)
     if(Field.Key!=TEXT("on")&&Field.Key!=TEXT("dimming")&&Field.Key!=TEXT("temperatureK")) return false;
    if(Override->HasField(TEXT("on"))) {bool V; if(!Override->TryGetBoolField(TEXT("on"),V)) return false;}
    if(Override->HasField(TEXT("dimming"))) {double V; if(!Override->TryGetNumberField(TEXT("dimming"),V)||!FMath::IsFinite(V)||V<0.||V>1.) return false;}
    if(Override->HasField(TEXT("temperatureK"))) {double V; if(!Override->TryGetNumberField(TEXT("temperatureK"),V)||!FMath::IsFinite(V)||V<1800.||V>10000.) return false;}
    FixtureOverrides.Add(FString(*Entry.Key),Override);
   }
  }
 }
 struct FLightPlan {ALight* Actor; double Intensity; double Temperature;}; TArray<FLightPlan> LightingPlan;
 if(LightingBindings.IsValid()) {
  const TArray<TSharedPtr<FJsonValue>>* FixtureList;
  if(!LightingBindings->TryGetArrayField(TEXT("fixtures"),FixtureList)) return false;
  TSet<FString> KnownFixtureIds;
  for(auto& FixtureValue:*FixtureList) {
   auto Fixture=FixtureValue->AsObject(); FString Id; double FixtureLumens,FixtureTemperatureK;
   if(!Fixture->TryGetStringField(TEXT("id"),Id)||!Fixture->TryGetNumberField(TEXT("lumens"),FixtureLumens)
    ||!Fixture->TryGetNumberField(TEXT("temperatureK"),FixtureTemperatureK)) return false;
   KnownFixtureIds.Add(Id);
   auto LightActor=Cast<ALight>(Actors.FindRef(TEXT("Light_")+Id)); if(!LightActor) return false;
   bool bOn=false; double Dimming=1.; double EffectiveTemperature=FixtureTemperatureK;
   if(auto Found=FixtureOverrides.Find(Id)) {
    (*Found)->TryGetBoolField(TEXT("on"),bOn);
    if(!(*Found)->TryGetNumberField(TEXT("dimming"),Dimming)) Dimming=1.;
    (*Found)->TryGetNumberField(TEXT("temperatureK"),EffectiveTemperature);
   }
   LightingPlan.Add({LightActor,bOn?FixtureLumens*Dimming:0.,EffectiveTemperature});
  }
  // Same "unconsumed key names something that does not exist" abort as
  // surfaceOverrides below -- a lighting.fixtures id not among this
  // project's actual fixtures is a stop condition, not a silent no-op.
  for(auto& Pair:FixtureOverrides) if(!KnownFixtureIds.Contains(Pair.Key)) return false;
 } else if(FixtureOverrides.Num()>0) return false; // fixtures named, but this project has none at all
 // W04: per-surface overrides, resolved and validated fully here (still no
 // scene mutation yet) so a bad override aborts before ANY change, same as
 // every check above. Mirrors unreal/surface_finish_overrides.py's
 // resolve_finish() exactly -- same finish-settings.json roles/
 // variantOverrides and study.json settings.variants palette -- so Blender/
 // editor/walkthrough never disagree about what a (kind, variant, override)
 // combination looks like. Absent SurfaceBindings/FinishDocument/
 // StudyVariants (a pre-W04 project) just means there is nothing to plan.
 struct FSurfaceAssignment {UStaticMeshComponent* Component; int32 Slot; UMaterialInterface* Base; FLinearColor Color; float Roughness;};
 TArray<FSurfaceAssignment> SurfacePlan;
 if(SurfaceBindings.IsValid()&&FinishDocument.IsValid()&&StudyVariants.IsValid()) {
  const TSharedPtr<FJsonObject>* SurfacesObj;
  if(!SurfaceBindings->TryGetObjectField(TEXT("surfaces"),SurfacesObj)) return false;
  // W04/W07-G1: surfaceOverrides must be validated with the same rigour as
  // unreal/study_state.py's validate_surface_overrides() -- a PRESENT value
  // of the wrong type, an override naming an id that is not an actual bound
  // surface (unknown id, no-surface, or a different room), or an override
  // object with an unknown field/out-of-range value must all abort the
  // whole apply, not be silently skipped or ignored one field at a time.
  // W07-G1: each room's OWN surfaceOverrides dict (roomStates[*].
  // surfaceOverrides) is always required and always an object (2.0.0 has no
  // "predates this field" schema any more), unlike the pre-G1 single
  // top-level field's 1.0.0 exemption.
  auto IsHex6=[](const FString& S){
   if(S.Len()!=6) return false;
   for(TCHAR C:S) {
    const bool bOk=(C>=TEXT('0')&&C<=TEXT('9'))||(C>=TEXT('a')&&C<=TEXT('f'))||(C>=TEXT('A')&&C<=TEXT('F'));
    if(!bOk) return false;
   }
   return true;
  };
  TMap<FString,TSet<FString>> ConsumedOverrideKeysByRoom;
  const TSharedPtr<FJsonObject>* RolesObj;
  if(!FinishDocument->TryGetObjectField(TEXT("roles"),RolesObj)) return false;
  const TSharedPtr<FJsonObject>* VariantOverridesObj=nullptr;
  FinishDocument->TryGetObjectField(TEXT("variantOverrides"),VariantOverridesObj);
  for(auto& SurfaceEntry:(*SurfacesObj)->Values) {
   auto Info=SurfaceEntry.Value->AsObject(); FString Status,Kind,SurfaceRoomId;
   if(!Info->TryGetStringField(TEXT("status"),Status)||Status!=TEXT("bound")) continue;
   if(!Info->TryGetStringField(TEXT("kind"),Kind)) return false;
   if(!Info->TryGetStringField(TEXT("roomId"),SurfaceRoomId)) return false;
   auto SurfaceRoomState=GetRoomState(SurfaceRoomId); if(!SurfaceRoomState) return false;
   FString RoomVariant; if(!(*SurfaceRoomState)->TryGetStringField(TEXT("variant"),RoomVariant)) return false;
   const TSharedPtr<FJsonObject>* OverridesObj;
   if(!(*SurfaceRoomState)->TryGetObjectField(TEXT("surfaceOverrides"),OverridesObj)) return false;
   // .Key is UE::FSharedString here (FJsonObject::Values), not FString --
   // FString(*Entry.Key) is the existing conversion idiom already used above
   // for the Bindings->Values loop.
   const FString SurfaceId=FString(*SurfaceEntry.Key);
   const TSharedPtr<FJsonObject>* Override=nullptr;
   if((*OverridesObj)->TryGetObjectField(SurfaceEntry.Key,Override)) {
    ConsumedOverrideKeysByRoom.FindOrAdd(SurfaceRoomId).Add(SurfaceId);
    for(auto& Field:(*Override)->Values)
     if(Field.Key!=TEXT("variant")&&Field.Key!=TEXT("colorHex")&&Field.Key!=TEXT("roughness")) return false;
    // W04 review v2 R4: a field that IS present must be fetched successfully
    // (right JSON type) AND satisfy its range -- TryGet*Field returning
    // false (wrong type, e.g. colorHex:123 or roughness:"bad") must reject,
    // not be treated the same as the field being absent. Checking HasField()
    // first is what the previous version was missing: `TryGet(...)&&!Valid`
    // silently let a present-but-wrong-type field fall through unchecked.
    if((*Override)->HasField(TEXT("colorHex"))) {
     FString OverrideColorCheck;
     if(!(*Override)->TryGetStringField(TEXT("colorHex"),OverrideColorCheck)||!IsHex6(OverrideColorCheck)) return false;
    }
    if((*Override)->HasField(TEXT("roughness"))) {
     double OverrideRoughnessCheck;
     if(!(*Override)->TryGetNumberField(TEXT("roughness"),OverrideRoughnessCheck)||
        !FMath::IsFinite(OverrideRoughnessCheck)||OverrideRoughnessCheck<0.||OverrideRoughnessCheck>1.) return false;
    }
    if((*Override)->HasField(TEXT("variant"))) {
     FString OverrideVariantCheck;
     if(!(*Override)->TryGetStringField(TEXT("variant"),OverrideVariantCheck)) return false;
    }
   }
   FString EffectiveVariant=RoomVariant;
   if(Override) (*Override)->TryGetStringField(TEXT("variant"),EffectiveVariant);
   TSharedPtr<FJsonObject> Detail;
   const TSharedPtr<FJsonObject>* ForVariant;
   if(VariantOverridesObj&&(*VariantOverridesObj)->TryGetObjectField(EffectiveVariant,ForVariant)) {
    const TSharedPtr<FJsonObject>* KindOverride;
    if((*ForVariant)->TryGetObjectField(Kind,KindOverride)) Detail=*KindOverride;
   }
   if(!Detail.IsValid()) {
    const TSharedPtr<FJsonObject>* Base;
    if(!(*RolesObj)->TryGetObjectField(Kind,Base)) return false;
    Detail=*Base;
   }
   FString PaletteRole=Kind; Detail->TryGetStringField(TEXT("paletteRole"),PaletteRole);
   const TSharedPtr<FJsonObject>* PaletteForVariant;
   if(!StudyVariants->TryGetObjectField(EffectiveVariant,PaletteForVariant)) return false;
   FString ColorHex; if(!(*PaletteForVariant)->TryGetStringField(PaletteRole,ColorHex)) return false;
   double Roughness=.6; Detail->TryGetNumberField(TEXT("roughness"),Roughness);
   if(Override) {
    FString OverrideColor; if((*Override)->TryGetStringField(TEXT("colorHex"),OverrideColor)) ColorHex=OverrideColor;
    double OverrideRoughness; if((*Override)->TryGetNumberField(TEXT("roughness"),OverrideRoughness)) Roughness=OverrideRoughness;
   }
   const TArray<TSharedPtr<FJsonValue>>* MeshesArray;
   if(!Info->TryGetArrayField(TEXT("meshes"),MeshesArray)) return false;
   for(auto& MeshValue:*MeshesArray) {
    auto MeshInfo=MeshValue->AsObject(); FString MeshActorLabel; int32 Slot;
    if(!MeshInfo->TryGetStringField(TEXT("actor"),MeshActorLabel)) return false;
    Slot=MeshInfo->GetIntegerField(TEXT("slot"));
    auto Actor=Cast<AStaticMeshActor>(Actors.FindRef(MeshActorLabel)); if(!Actor) return false;
    auto Component=Actor->GetStaticMeshComponent();
    if(Slot<0||Slot>=Component->GetNumMaterials()) return false;
    // W04 review v2 R1: load the parent by (surface, EFFECTIVE variant)
    // instead of reusing whatever MID/asset currently happens to sit in the
    // slot. import_study.py now builds one parametric marker material per
    // (surface, variant) -- each with that variant's own pattern already
    // baked in (planks/tile/plain noise) -- precisely so switching variant
    // (whole-scene, a per-surface override, a loaded scenario, A/B) changes
    // the actual pattern, not just the MID's Color/Roughness on top of
    // whichever pattern happened to be loaded last.
    UMaterialInterface* Base=LoadObject<UMaterialInterface>(nullptr,
     *(TEXT("/Game/Generated/Finishes/M_Surf_")+SurfaceId+TEXT("_")+EffectiveVariant));
    if(!Base) return false;
    SurfacePlan.Add({Component,Slot,Base,FLinearColor(FColor::FromHex(ColorHex)),(float)Roughness});
   }
  }
  // Any surfaceOverrides key that was never consumed above names something
  // that is not an actually-bound surface in THAT room at all (unknown id,
  // a registered id whose status is not "bound", or a different room) --
  // same as Python's resolve_overrides() treating that as a stop condition,
  // not something to silently drop. Checked once per room here (rather than
  // inline in the surface loop above) so a surface id that never appears in
  // SurfacesObj at all is still caught.
  for(auto& RoomEntry:(*RoomStatesObj)->Values) {
   auto RoomObj=RoomEntry.Value->AsObject(); if(!RoomObj.IsValid()) return false;
   const TSharedPtr<FJsonObject>* RoomOverridesObj;
   if(!RoomObj->TryGetObjectField(TEXT("surfaceOverrides"),RoomOverridesObj)) return false;
   const TSet<FString>& Consumed=ConsumedOverrideKeysByRoom.FindOrAdd(FString(*RoomEntry.Key));
   for(auto& OverrideEntry:(*RoomOverridesObj)->Values)
    if(!Consumed.Contains(FString(*OverrideEntry.Key))) return false;
  }
 }
 // W07-G2: doorStates -- resolved and validated fully here (still no scene
 // mutation yet), same discipline as surfaceOverrides above. A doorId naming
 // something that is not an actually-openable connection (unknown id, or a
 // real 'open'-operation door with no leaf at all) is a stop condition, not
 // silently dropped (mirrors circulation.py's resolve_door_overrides()).
 struct FDoorLeafPlan {AActor* Actor; bool bRotate; FRotator Rotation; FVector Location;};
 TArray<FDoorLeafPlan> DoorPlan;
 const TSharedPtr<FJsonObject>* DoorStatesObj;
 if(!State->TryGetObjectField(TEXT("doorStates"),DoorStatesObj)) return false;
 TSet<FString> ConsumedDoorKeys;
 for(auto& Connection:Connections) {
  if(!Connection.bOpenable) continue;
  bool bOpen=false;
  const TSharedPtr<FJsonObject>* Override;
  if((*DoorStatesObj)->TryGetObjectField(Connection.Id,Override)) {
   ConsumedDoorKeys.Add(Connection.Id);
   for(auto& Field:(*Override)->Values) if(Field.Key!=TEXT("open")) return false;
   if(!(*Override)->TryGetBoolField(TEXT("open"),bOpen)) return false;
  }
  for(auto& Leaf:Connection.Leaves) {
   AActor* LeafActor=Actors.FindRef(Leaf.Actor); if(!LeafActor) return false;
   if(Leaf.bHasYaw) {
    DoorPlan.Add({LeafActor,true,FRotator(0,bOpen?Leaf.OpenYawDeltaDeg:0.,0),FVector::ZeroVector});
   } else if(Leaf.bHasOffset) {
    if(!DoorLeafSpawnLocation.Contains(Leaf.Actor)) DoorLeafSpawnLocation.Add(Leaf.Actor,LeafActor->GetActorLocation());
    const FVector Base=DoorLeafSpawnLocation[Leaf.Actor];
    DoorPlan.Add({LeafActor,false,FRotator::ZeroRotator,bOpen?Base+Leaf.OpenOffsetCm:Base});
   }
  }
 }
 // Any doorStates key never consumed above names something that is not an
 // actually-openable door here at all -- same stop-condition treatment as
 // an unresolved surfaceOverrides/fixtures key.
 for(auto& Pair:(*DoorStatesObj)->Values) if(!ConsumedDoorKeys.Contains(FString(*Pair.Key))) return false;
 for(auto& Item:Plan) Item.Component->SetMaterial(Item.Slot,Item.Material);
 for(auto& Item:SurfacePlan) {
  auto Mid=UMaterialInstanceDynamic::Create(Item.Base,Item.Component);
  Mid->SetVectorParameterValue(TEXT("Color"),Item.Color);
  Mid->SetScalarParameterValue(TEXT("Roughness"),Item.Roughness);
  Item.Component->SetMaterial(Item.Slot,Mid);
 }
 for(auto& Item:DoorPlan) {
  Item.Actor->Modify();
  if(Item.bRotate) Item.Actor->SetActorRotation(Item.Rotation,ETeleportType::TeleportPhysics);
  else Item.Actor->SetActorLocation(Item.Location,false,nullptr,ETeleportType::TeleportPhysics);
 }
 Az=FMath::DegreesToRadians(Az); El=FMath::DegreesToRadians(El);
 Sun->SetActorRotation(FVector(-sin(Az)*cos(El),cos(Az)*cos(El),-sin(El)).Rotation());
 // W06: night disables the sun's direct light and the daytime sky
 // (SkyAtmosphere/SkyLight) entirely -- fixture lights are the only source,
 // a common fixed (no-moonlight) environment, same contract as
 // study_controls.apply_state(). Day restores both to this state's own Lux,
 // never a re-derived value.
 const bool bNight=LightingMode==TEXT("night");
 Sun->GetLightComponent()->SetIntensity(bNight?0.:Lux);
 for(auto SkyLabel:{TEXT("Sky"),TEXT("SkyLight")})
  if(auto SkyActor=Actors.FindRef(SkyLabel)) SkyActor->SetActorHiddenInGame(bNight);
 for(auto& Item:LightingPlan) {
  Item.Actor->GetLightComponent()->SetIntensity(Item.Intensity);
  Item.Actor->GetLightComponent()->SetTemperature(Item.Temperature);
 }
 Post->Settings.AutoExposureMinBrightness=EV; Post->Settings.AutoExposureMaxBrightness=EV;
 return true;
}
void AWalkthroughCharacter::SetFinish(const FString& Name,const FString& Label) {
 // W07-G2: the finish keys only ever affect whichever room the player is
 // CURRENTLY standing in, and only while that room is actually in the edit
 // scope (spec section 3: "室移動だけで材質...を変更しません" -- a non-edit
 // room like the hall has no roomState to change at all, and must not fall
 // back to silently touching whatever room was last edited).
 // GetObjectField() returns a mutable reference into State's own nested
 // object graph (not a copy), so this mutates State in place.
 if(!bReady) return;
 if(!IsCurrentRoomEditable()) {Message=TEXT("この部屋は仕上げ編集の対象外です（LDK・洋室のみ）"); return;}
 auto RoomState=State->GetObjectField(TEXT("roomStates"))->GetObjectField(CurrentRoomId);
 FString Old=RoomState->GetStringField(TEXT("variant")); RoomState->SetStringField(TEXT("variant"),Name);
 if(!ApplyConditions()) {RoomState->SetStringField(TEXT("variant"),Old);Message=TEXT("この仕上げは利用できません");} else Message=Label;
}
void AWalkthroughCharacter::SetSun(float Elevation) {
 if(!bReady) return;
 // Copying the TSharedPtr would alias the same FJsonObject as State, so the
 // in-place SetNumberField/RemoveField below would mutate Backup too. Copying
 // the object itself copies its Values map, which is enough to roll back
 // these two top-level fields (SetSun never touches nested objects like camera).
 auto Backup=MakeShared<FJsonObject>(*State);
 State->SetNumberField(TEXT("elevationDeg"),Elevation); State->RemoveField(TEXT("solar"));
 if(ApplyConditions()) Message=TEXT("手動太陽角度（未校正）");
 else {State=Backup; Message=TEXT("太陽角度を変更できません");}
}
void AWalkthroughCharacter::InteractDoor() {
 // W07-G2 spec section 2: near a door, facing it (FindNearestDoor(), run
 // every Tick), toggle open/closed. ApplyConditions() moves every leaf
 // per the CANDIDATE doorStates BEFORE this checks Safe() against the
 // player's own capsule -- reusing the exact same "is the player's own
 // position still clear of blocking geometry" check spawn/Restore() use,
 // rather than a separate leaf-vs-capsule overlap test, is deliberate: it
 // is the one query this project already trusts for "does something now
 // occupy where I am standing". A rejected toggle leaves the door and
 // State exactly as they were (spec: "元状態を維持して理由を表示").
 if(!bReady||NearestDoorId.IsEmpty()) return;
 const FString Label=DoorPromptLabel();
 const bool bWasOpen=GetDoorOpen(NearestDoorId);
 auto DoorStatesObj=State->GetObjectField(TEXT("doorStates"));
 const bool bHadEntry=DoorStatesObj->HasField(NearestDoorId);
 TSharedPtr<FJsonObject> Backup=bHadEntry?DoorStatesObj->GetObjectField(NearestDoorId):nullptr;
 auto NewOverride=MakeShared<FJsonObject>(); NewOverride->SetBoolField(TEXT("open"),!bWasOpen);
 DoorStatesObj->SetObjectField(NearestDoorId,NewOverride);
 auto Revert=[&]() {
  if(bHadEntry) DoorStatesObj->SetObjectField(NearestDoorId,Backup); else DoorStatesObj->RemoveField(NearestDoorId);
  ApplyConditions(); // best-effort: puts the leaf back to bWasOpen
 };
 if(!ApplyConditions()) {Revert(); Message=TEXT("扉を開閉できません"); return;}
 if(!Safe(GetActorLocation())) {Revert(); Message=TEXT("扉を動かせません（干渉しています）。近づきすぎている可能性があります"); return;}
 Message=(!bWasOpen?TEXT("開けました："):TEXT("閉じました："))+Label;
}
// Labels match study_controls.py's register_menu() so the walkthrough and the
// editor menu describe the same variants identically.
void AWalkthroughCharacter::Finish1(){SetFinish(TEXT("natural"),TEXT("白壁・ナチュラルオーク"));} void AWalkthroughCharacter::Finish2(){SetFinish(TEXT("warm"),TEXT("グレージュ・ウォルナット"));}
void AWalkthroughCharacter::Finish3(){SetFinish(TEXT("reference"),TEXT("石調の床・木板天井"));} void AWalkthroughCharacter::SunLow(){SetSun(30);} void AWalkthroughCharacter::SunHigh(){SetSun(60);}
FString AWalkthroughCharacter::CurrentVariantLabel() const {
 // W07-G2: reflects whichever room the player is CURRENTLY standing in --
 // empty (HUD's own "－" placeholder) while standing in a non-edit room
 // like the hall, which has no roomState/variant to show at all.
 if(!bReady||!State.IsValid()||!IsCurrentRoomEditable()) return FString();
 const TSharedPtr<FJsonObject>* RoomStatesObj;
 if(!State->TryGetObjectField(TEXT("roomStates"),RoomStatesObj)) return FString();
 const TSharedPtr<FJsonObject>* RoomState;
 if(!(*RoomStatesObj)->TryGetObjectField(CurrentRoomId,RoomState)) return FString();
 FString Variant; if(!(*RoomState)->TryGetStringField(TEXT("variant"),Variant)) return FString();
 if(Variant==TEXT("natural")) return TEXT("白壁・ナチュラルオーク");
 if(Variant==TEXT("warm")) return TEXT("グレージュ・ウォルナット");
 if(Variant==TEXT("reference")) return TEXT("石調の床・木板天井");
 return Variant;
}
// W05: distinguishes a date/time-derived sun angle from a manual one on the
// HUD -- State->solar is the same generic passthrough FJsonObject already
// round-tripped through F5/F9 with no C++ changes (SetSun() clears it on a
// manual change; study_controls.py's set_sun_case()/daylight A/B set it).
FString AWalkthroughCharacter::CurrentSolarLabel() const {
 if(!bReady||!State.IsValid()) return FString();
 const TSharedPtr<FJsonObject>* Solar;
 if(!State->TryGetObjectField(TEXT("solar"),Solar)) return TEXT("手動角度（未校正）");
 FString Stamp,LocationStatus,NorthStatus;
 (*Solar)->TryGetStringField(TEXT("localTimestamp"),Stamp);
 (*Solar)->TryGetStringField(TEXT("locationStatus"),LocationStatus);
 (*Solar)->TryGetStringField(TEXT("northStatus"),NorthStatus);
 const bool bEstimated=LocationStatus!=TEXT("verified")||NorthStatus!=TEXT("verified");
 return Stamp+(bEstimated?TEXT("（日時・位置概算）"):TEXT("（日時・入力確認済み）"));
}
// W06: night/day + a standing reminder that brightness/colour here are still
// unmeasured estimated profiles, not calibrated site lighting (spec:
// 'HUDに夜間モードと明るさが仮仕様であることを表示します'). State->lighting
// is the same generic passthrough FJsonObject already round-tripped through
// F5/F9 with no extra C++ needed for persistence itself.
FString AWalkthroughCharacter::CurrentLightingLabel() const {
 if(!bReady||!State.IsValid()) return FString();
 const TSharedPtr<FJsonObject>* Lighting; FString Mode=TEXT("day");
 if(State->TryGetObjectField(TEXT("lighting"),Lighting)) (*Lighting)->TryGetStringField(TEXT("mode"),Mode);
 return Mode==TEXT("night")?TEXT("夜間（仮仕様）"):TEXT("昼間");
}
void AWalkthroughCharacter::SaveView() {
 if(!bReady) return;
 FString RecoveryMessage;
 if(!RecoverSaveIfNeeded(RecoveryMessage)) {
  // Backup already holds an unrecovered previous save (final replace failed
  // last time, and so did restoring it back). Refuse to save until that is
  // resolved: treating Path-missing as "first save" here would skip the
  // rename-aside step entirely, and a later legitimate rename-aside could
  // then silently overwrite this same Backup, destroying the last known-good
  // data with no path back to it.
  Message=RecoveryMessage; return;
 }
 auto Camera=MakeShared<FJsonObject>(); Camera->SetArrayField(TEXT("locationCm"),Numbers(Eye->GetComponentLocation()));
 auto R=Controller->GetControlRotation(); Camera->SetArrayField(TEXT("rotationDeg"),Numbers(FVector(R.Pitch,R.Yaw,0)));
 Camera->SetNumberField(TEXT("lensMm"),18./tan(FMath::DegreesToRadians(Eye->FieldOfView/2)));
 State->SetObjectField(TEXT("camera"),Camera);
 // W07-G2 spec section 4: F5 records the native walkthrough's own current
 // room/level as `walkthrough` attribution -- doorStates/roomStates
 // themselves are already kept current in State by every SetFinish()/
 // InteractDoor() call, nothing extra to do for those here.
 auto WalkthroughInfo=MakeShared<FJsonObject>();
 WalkthroughInfo->SetStringField(TEXT("profileId"),ProfileId);
 WalkthroughInfo->SetStringField(TEXT("roomId"),CurrentRoomId);
 if(const FRoomInfo* Info=Rooms.Find(CurrentRoomId)) WalkthroughInfo->SetNumberField(TEXT("level"),Info->Level);
 State->SetObjectField(TEXT("walkthrough"),WalkthroughInfo);
 FString Text; FJsonSerializer::Serialize(State.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
 FString Path,Backup; SavedViewPaths(Path,Backup); const FString Tmp=Path+TEXT(".tmp");
 // IFileManager::Move() returns bool (true on success), not ECopyResult; a
 // previous `==COPY_OK` (0) compared a bool against an unscoped enum, which
 // usual arithmetic conversions evaluate as (int)bool==(int)enum, inverting
 // the result (success/true(1)==0 is false; failure/false(0)==0 is true).
 // Confirmed via a read-only-file test: Move() logged an actual delete
 // failure yet the old comparison still reported success. Fixed by using the
 // bool directly.
 //
 // That alone still left the previous save unprotected mid-replace, though:
 // FFileManagerGeneric::Move(Path,Tmp,Replace=true,...) deletes Path first and
 // only then renames Tmp over it (Engine/Source/Runtime/Core/Private/HAL/
 // FileManagerGeneric.cpp), so a MoveFile failure *after* that delete
 // succeeds would return false having already destroyed the old save. Rename
 // any existing save out of the way first (a rename, survives on disk, not a
 // delete) and only remove that backup once Tmp has actually replaced Path;
 // restore it if the final rename fails. This is deliberately not the same
 // Move() wrapped differently -- Path is never deleted up front.
 bool bSuccess=false;
 if(FFileHelper::SaveStringToFile(Text,*Tmp,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)) {
  if(!IFileManager::Get().FileExists(*Path)) {
   bSuccess=IFileManager::Get().Move(*Path,*Tmp,true,true); // first save, nothing to protect
  } else if(IFileManager::Get().Move(*Backup,*Path,true,true)) { // rename old save aside
#if !UE_BUILD_SHIPPING
   // Test-only, inert unless -RyukaFaultSave is on the command line (never
   // passed on a real launch): deterministically reproduces "final replace
   // fails AND restoring Backup back also fails" by making a real directory
   // occupy the just-freed target name, so both real Move() calls below fail
   // via genuine Windows rename semantics -- not a simulated return value.
   // This is the fixed, reproducible fault-injection point exercised by
   // -RyukaFaultSave in Tick(), replacing an earlier FileSystemWatcher race
   // that was real but not guaranteed to land on this exact step every run.
   if(FParse::Param(FCommandLine::Get(),TEXT("RyukaFaultSave"))) IFileManager::Get().MakeDirectory(*Path,false);
#endif
   if(IFileManager::Get().Move(*Path,*Tmp,true,true)) {
    bSuccess=true;
    IFileManager::Get().Delete(*Backup,false,true,true);
   } else if(!IFileManager::Get().Move(*Path,*Backup,true,true)) {
    // Restoring the previous save from Backup failed too: Path is still
    // missing and Backup still holds it. Do not fall through to the generic
    // failure message below -- leave Backup exactly as it is (the guard at
    // the top of this function keeps every later save from touching it
    // until this is resolved) and say so explicitly instead of silently
    // reporting a plain "failed to save".
    // Relative name, not the absolute Backup path -- see the matching note
    // in RecoverSaveIfNeeded() above.
    Message=TEXT("保存に失敗し、旧データの復元にも失敗しました。バックアップ「")+SavedViewName()+TEXT(".bak」が残っています。復旧するまで保存できません。");
    return;
   }
   // If the rename-to-Backup step itself failed, Path was never touched and
   // the previous save is intact; bSuccess stays false either way here. If
   // the restore-from-Backup above succeeded, the previous save is back at
   // Path and Backup is gone; bSuccess also stays false here, correctly
   // reporting that this save attempt itself did not go through.
  }
 }
 Message=bSuccess?TEXT("視点と条件を保存しました"):TEXT("保存に失敗しました");
}
void AWalkthroughCharacter::ToggleMouse() {auto PC=Cast<APlayerController>(Controller); PC->bShowMouseCursor=!PC->bShowMouseCursor; if(PC->bShowMouseCursor) PC->SetInputMode(FInputModeGameAndUI()); else PC->SetInputMode(FInputModeGameOnly());}
void AWalkthroughCharacter::SetupPlayerInputComponent(UInputComponent* I) {
 Super::SetupPlayerInputComponent(I);
 I->BindKey(EKeys::One,IE_Pressed,this,&AWalkthroughCharacter::Finish1); I->BindKey(EKeys::Two,IE_Pressed,this,&AWalkthroughCharacter::Finish2); I->BindKey(EKeys::Three,IE_Pressed,this,&AWalkthroughCharacter::Finish3);
 I->BindKey(EKeys::Four,IE_Pressed,this,&AWalkthroughCharacter::SunLow); I->BindKey(EKeys::Five,IE_Pressed,this,&AWalkthroughCharacter::SunHigh);
 I->BindKey(EKeys::F5,IE_Pressed,this,&AWalkthroughCharacter::SaveView); I->BindKey(EKeys::F9,IE_Pressed,this,&AWalkthroughCharacter::RestoreView); I->BindKey(EKeys::Tab,IE_Pressed,this,&AWalkthroughCharacter::ToggleMouse);
 I->BindKey(EKeys::E,IE_Pressed,this,&AWalkthroughCharacter::InteractDoor);
}
void AWalkthroughCharacter::Tick(float Delta) {
 Super::Tick(Delta); auto PC=Cast<APlayerController>(Controller);
 if(PC&&!bInitialized) {
  bInitialized=true;
  // Clamping ControlRotation.Pitch by hand after AddControllerPitchInput does
  // not work here: that input is only applied to ControlRotation by the
  // PlayerController's own update, which runs after this Tick, so a manual
  // clamp always reads last frame's value. PlayerCameraManager's view pitch
  // range is the standard place this limit belongs; it is enforced as part
  // of that same update, so it actually catches every frame's input.
  if(PC->PlayerCameraManager) {PC->PlayerCameraManager->ViewPitchMin=-80.; PC->PlayerCameraManager->ViewPitchMax=80.;}
  RestoreView(); PC->bShowMouseCursor=false; PC->SetInputMode(FInputModeGameOnly());
 }
 // Furniture/wall collision is left to CharacterMovement's own sweep/slide
 // (below, AddMovementInput is always called for a non-zero direction) so
 // diagonal movement along a wall does not stall. The room polygon boundary
 // has no physical wall at openings, so it is enforced here instead: if the
 // actor ends up outside it, correct back to a nearby point that is inside.
 // This runs after Super::Tick(), which is guaranteed (not just observed) to
 // have already applied the previous frame's AddMovementInput here:
 // UMovementComponent's constructor sets bTickBeforeOwner=true, and its
 // RegisterComponentTickFunctions (Engine/Source/Runtime/Engine/Private/
 // Components/MovementComponent.cpp) adds itself as a tick prerequisite of
 // the owning Actor's PrimaryActorTick when that is set, so the engine's own
 // tick scheduler -- not this project's Tick() -- orders CharacterMovement's
 // component tick before this Character's Tick(). No custom tick machinery
 // is added here to rely on that; it is the engine's default for any
 // ACharacter/CharacterMovementComponent pair, unchanged in this project.
 if(bReady) {
  // W07-G2: which room "here" is (for the boundary relaxation Safe() below
  // uses, the finish keys' editability, and the HUD's room label) is
  // resolved BEFORE the safety correction, from wherever the player already
  // is -- not re-derived from the (possibly-corrected) position afterward.
  UpdateCurrentRoom();
  FindNearestDoor();
  const FVector Current=GetActorLocation();
  if(!Safe(Current)) {
   // Safe(), not InsideRoom(): the normal branch below records Current as
   // LastSafeLocation, so it must confirm no furniture overlap too, or a
   // sweep that (rarely) ends up embedded in geometry would be recorded as
   // a safe point to fall back to later.
   //
   // Candidates must likewise be Safe() (boundary AND furniture/wall
   // overlap), not just InsideRoom(): a point picked by keeping one axis
   // from LastSafeLocation can itself sit inside a different piece of
   // furniture (e.g. rounding a corner). All room edges here are
   // axis-aligned, so try keeping each axis independently before falling
   // back to a binary search along the segment.
   FVector Candidate;
   const FVector KeepX(Current.X,LastSafeLocation.Y,Current.Z);
   const FVector KeepY(LastSafeLocation.X,Current.Y,Current.Z);
   if(Safe(KeepX)) Candidate=KeepX;
   else if(Safe(KeepY)) Candidate=KeepY;
   else {
    FVector SafePoint=LastSafeLocation,UnsafePoint=Current;
    for(int32 I=0;I<12;I++) {
     FVector Mid=FMath::Lerp(SafePoint,UnsafePoint,0.5f);
     if(Safe(Mid)) SafePoint=Mid; else UnsafePoint=Mid;
    }
    Candidate=SafePoint;
   }
   // Candidate being Safe() only proves the endpoint is clear, not the path to
   // it: teleporting there could still cut through furniture standing between
   // Current and Candidate. Sweep the move so a mid-path hit stops the actor
   // there instead, then re-check the landing spot before trusting it.
   FHitResult Hit;
   SetActorLocation(Candidate,true,&Hit,ETeleportType::TeleportPhysics);
   GetCharacterMovement()->Velocity=FVector::ZeroVector;
   FVector Landed=GetActorLocation();
   if(!Safe(Landed)) {
    // The sweep toward Candidate was itself blocked partway and the landing
    // spot is still unsafe. A non-sweeping teleport to LastSafeLocation here
    // would ignore anything between Landed and LastSafeLocation -- "the old
    // point was safe" says nothing about the path from here to it. Sweep
    // there too instead of assuming the direct line is clear.
    SetActorLocation(LastSafeLocation,true,&Hit,ETeleportType::TeleportPhysics);
    GetCharacterMovement()->Velocity=FVector::ZeroVector;
    Landed=GetActorLocation();
   }
   // Only ever record a Safe() landing spot. If both sweeps still leave the
   // actor unsafe, there is no correction left to retry on the next Tick --
   // continuing to allow AddMovementInput/SaveView from here would let the
   // player keep moving and saving from a position no longer guaranteed
   // reachable back to safety. Stop instead: only F9's Restore() (which
   // requires and re-confirms a Safe start point, and explicitly restores
   // MOVE_Walking) may resume play. This is deliberately not a silent
   // teleport to LastSafeLocation -- that would ignore collision on the way
   // there, exactly what the sweeps above exist to avoid.
   if(Safe(Landed)) LastSafeLocation=Landed;
   else {
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    bReady=false;
    Message=TEXT("安全な位置へ戻れません。F9で復元してください");
   }
  } else LastSafeLocation=Current;
 }
#if !UE_BUILD_SHIPPING
 // Everything down to the matching #endif below (all three native
 // regression-test blocks: -RyukaFaultSave, -RyukaVerifyRecovery,
 // -RyukaBoundaryFaultTest) is compiled out of shipping builds entirely, not
 // just the fault-injection line inside SaveView(). None of it runs, and
 // none of these command-line switches have any effect, unless a developer
 // build was explicitly launched with one of them.
 // -RyukaFaultSave: deterministic, native, single-process regression for the
 // "final replace fails AND restoring Backup also fails" path (required fix
 // A). The actual fault is injected inside SaveView() itself (see the
 // MakeDirectory call there); everything here just drives real SaveView()/
 // RestoreView() calls and inspects real files on disk -- no part of the
 // save/restore logic under test is mocked or bypassed. The obstruction is
 // deliberately left on disk when this finishes so a separate plain relaunch
 // (no switches -- see -RyukaVerifyRecovery below) can independently confirm
 // it is recognized after a real process restart, and a relaunch after the
 // obstruction is removed can independently confirm auto-recovery -- both
 // outside this process, since neither claim can be proven by an in-process
 // test alone. Inert unless -RyukaFaultSave is on the command line.
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaFaultSave"))) {
  static bool Done=false;
  if(!Done&&GetWorld()->GetTimeSeconds()>1) {
   Done=true;
   auto ReadAbs=[](const FString& AbsPath)->FString{FString S;FFileHelper::LoadFileToString(S,*AbsPath);return S;};
   FString Path,Backup; SavedViewPaths(Path,Backup);
   // Non-recursive (Tree=false): a leftover obstruction directory from a
   // prior faulted run here is always empty (this test alone ever creates
   // it, via SaveView()'s MakeDirectory), so a plain (non-recursive)
   // RemoveDirectory removes it; if anything unexpected ever put real
   // content there, Windows refuses to remove a non-empty directory and this
   // silently leaves it in place rather than deleting whatever is inside it.
   IFileManager::Get().Delete(*Path,false,true,true);
   IFileManager::Get().DeleteDirectory(*Path,false,false);
   IFileManager::Get().Delete(*Backup,false,true,true);
   IFileManager::Get().DeleteDirectory(*Backup,false,false);
   SaveView(); // Path did not exist: plain first save, no injection runs yet
   const FString Original=ReadAbs(Path);
   const bool CreatedInitialSave=!Original.IsEmpty();
   SaveView(); // Path exists now: triggers the injected double failure
   const FString AfterFault=ReadAbs(Backup); const FString MessageAfterFault=Message;
   const bool PreservedAfterFault=AfterFault==Original&&!Original.IsEmpty();
   SaveView(); // repeat F5 while still faulted: must not touch Backup
   const FString AfterRepeat=ReadAbs(Backup); const FString MessageAfterRepeat=Message;
   const bool PreservedAfterRepeat=AfterRepeat==Original;
   RestoreView(); // simulate F9 while still faulted
   const bool BlockedOnF9=!bReady; const FString MessageAfterF9=Message;
   const bool Passed=CreatedInitialSave&&PreservedAfterFault&&MessageAfterFault.Contains(TEXT("復旧"))
    &&PreservedAfterRepeat&&MessageAfterRepeat.Contains(TEXT("復旧"))&&BlockedOnF9&&MessageAfterF9.Contains(TEXT("復旧"));
   auto Result=MakeShared<FJsonObject>();
   Result->SetBoolField(TEXT("createdInitialSave"),CreatedInitialSave);
   Result->SetBoolField(TEXT("backupPreservedAfterFault"),PreservedAfterFault);
   Result->SetStringField(TEXT("messageAfterFault"),MessageAfterFault);
   Result->SetBoolField(TEXT("backupPreservedAfterRepeatSave"),PreservedAfterRepeat);
   Result->SetStringField(TEXT("messageAfterRepeatSave"),MessageAfterRepeat);
   Result->SetBoolField(TEXT("blockedOnF9WhileFaulted"),BlockedOnF9);
   Result->SetStringField(TEXT("messageAfterF9"),MessageAfterF9);
   Result->SetBoolField(TEXT("passed"),Passed);
   Result->SetStringField(TEXT("note"),TEXT("Obstruction left on disk on purpose -- relaunch with no switches (or -RyukaVerifyRecovery) to check restart recognition, then delete the directory at <project>/")+SavedViewName()+TEXT(" and relaunch again to check auto-recovery."));
   FString Out; FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Out));
   FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectSavedDir()/TEXT("walkthrough-fault-save.json")));
   FFileHelper::SaveStringToFile(Passed?TEXT("PASS"):TEXT("FAIL"),*(FPaths::ProjectSavedDir()/TEXT("walkthrough-fault-save.txt")));
  }
  if(Done) {FPlatformMisc::RequestExit(false); return;}
 }
 // -RyukaVerifyRecovery: read-only observer of whatever the normal startup
 // sequence already decided (Tick's !bInitialized block above calls
 // RestoreView() unconditionally on every launch, faulted or not); this
 // switch changes no decision, it only reports bReady/Message and exits, so
 // a launch with it is behaviorally identical to a real user's plain launch.
 // Used to independently confirm, via separate real process launches, that a
 // save-recovery state left by -RyukaFaultSave is (a) recognized after a
 // restart and (b) auto-recovered once the obstruction is removed.
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaVerifyRecovery"))) {
  static bool Done=false;
  if(!Done&&GetWorld()->GetTimeSeconds()>1) {
   Done=true;
   FString Path,Backup; SavedViewPaths(Path,Backup);
   auto Result=MakeShared<FJsonObject>();
   Result->SetBoolField(TEXT("ready"),bReady);
   Result->SetStringField(TEXT("message"),Message);
   Result->SetBoolField(TEXT("pathIsFile"),IFileManager::Get().FileExists(*Path));
   Result->SetBoolField(TEXT("backupExists"),IFileManager::Get().FileExists(*Backup));
   FString Out; FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Out));
   FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectSavedDir()/TEXT("walkthrough-recovery-check.json")));
  }
  if(Done) {FPlatformMisc::RequestExit(false); return;}
 }
 // -RyukaBoundaryFaultTest: deterministic, native regression for required fix
 // B (stop, don't keep playing, when both boundary-correction sweeps still
 // land unsafe) plus its F9 recovery. Uses real spawned blocking geometry (so
 // Safe()/Tick()'s own correction logic run completely unmodified and for
 // real) instead of relying on incidental room layout, so the outcome does
 // not depend on which generated project this runs against. Inert unless
 // -RyukaBoundaryFaultTest is on the command line.
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaBoundaryFaultTest"))) {
  static int32 Phase=0; static FVector L0,L1; static TArray<AStaticMeshActor*> Blockers;
  static bool P1Ready=false; static FString Msg1,Msg2,Msg3;
  auto Spawn=[this](const FVector& Center,const FVector& SizeCm)->AStaticMeshActor* {
   auto Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")); if(!Mesh) return nullptr;
   FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
   auto Actor=GetWorld()->SpawnActor<AStaticMeshActor>(Center,FRotator::ZeroRotator,Params); if(!Actor) return nullptr;
   auto Comp=Actor->GetStaticMeshComponent(); Comp->SetMobility(EComponentMobility::Movable);
   Comp->SetStaticMesh(Mesh); Actor->SetActorScale3D(SizeCm/100.);
   Comp->SetCollisionProfileName(TEXT("BlockAll")); Comp->RecreatePhysicsState();
   return Actor;
  };
  const double T=GetWorld()->GetTimeSeconds();
  if(Phase==0&&T>1) {
   Phase=1;
   if(!bReady) {Msg1=TEXT("初期状態が準備できていません"); Phase=9;}
   else {
    L0=LastSafeLocation;
    // March outward in a fixed direction from the known-Safe L0 until Safe()
    // first turns false: whatever boundary/furniture triggers that is a real,
    // marginal (a few cm) excursion -- not a deep artificial penetration from
    // teleporting onto a spawned blocker, which starts the actor already
    // embedded in solid geometry and makes the following sweep unreliable --
    // so the existing two-attempt correction (already reviewed and accepted)
    // gets a realistic case to recover within. This is a regression check
    // that the new stop logic below does not fire on an ordinary recoverable
    // excursion.
    FVector Probe=L0;
    for(int32 I=0;I<200&&Safe(Probe);I++) Probe+=FVector(5,0,0);
    SetActorLocation(Probe,false,nullptr,ETeleportType::TeleportPhysics);
   }
  } else if(Phase==1&&T>1.5) {
   P1Ready=bReady; Msg1=Message; L1=bReady?LastSafeLocation:L0;
   for(auto* B:Blockers) if(B) B->Destroy(); Blockers.Empty();
   Phase=2;
   if(P1Ready) {
    // One large blocker generously covering both the new Current test point
    // and L1 (the last known-safe point) plus margin: every candidate the
    // correction algorithm could reach -- KeepX, KeepY, the binary-search
    // segment between them, and L1 itself -- sits inside it, so both the
    // candidate sweep and the LastSafeLocation fallback sweep are guaranteed
    // to still land unsafe.
    Blockers.Add(Spawn(FMath::Lerp(L1,L1+FVector(300,300,0),0.5f),FVector(900,900,300)));
    SetActorLocation(L1+FVector(60,60,0),false,nullptr,ETeleportType::TeleportPhysics);
   }
  } else if(Phase==2&&T>2.2) {
   const bool Stopped=!bReady&&GetCharacterMovement()->MovementMode==MOVE_None&&GetCharacterMovement()->Velocity.IsNearlyZero();
   Msg2=Message;
   for(auto* B:Blockers) if(B) B->Destroy(); Blockers.Empty();
   RestoreView(); // simulate F9
   const bool Restored=bReady&&Safe(GetActorLocation()); Msg3=Message;
   const bool Passed=P1Ready&&Stopped&&Restored;
   auto Result=MakeShared<FJsonObject>();
   Result->SetBoolField(TEXT("recoveredWithinTwoAttempts"),P1Ready);
   Result->SetStringField(TEXT("messageAfterRecoverableExcursion"),Msg1);
   Result->SetBoolField(TEXT("stoppedAfterBothAttemptsFailed"),Stopped);
   Result->SetStringField(TEXT("messageAfterStop"),Msg2);
   Result->SetBoolField(TEXT("resumedAfterF9"),Restored);
   Result->SetStringField(TEXT("messageAfterF9"),Msg3);
   Result->SetBoolField(TEXT("passed"),Passed);
   FString Out; FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Out));
   FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectSavedDir()/TEXT("walkthrough-boundary-fault.json")));
   FFileHelper::SaveStringToFile(Passed?TEXT("PASS"):TEXT("FAIL"),*(FPaths::ProjectSavedDir()/TEXT("walkthrough-boundary-fault.txt")));
   Phase=9;
  }
  if(Phase==9) {FPlatformMisc::RequestExit(false); return;}
 }
#endif
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaSmoke"))&&GetWorld()->GetTimeSeconds()>3&&!bSmokeDone) {
  bSmokeDone=true; bool Passed=bReady;
  if(bReady) {
   const FVector Start=GetActorLocation(); FHitResult Hit;
   SetActorLocation(Start+FVector(2000,0,0),true,&Hit);
   Passed &= Hit.bBlockingHit && FVector::Dist2D(Start,GetActorLocation())<1900;
   RestoreView();
   // W07-G2: the profile's entry room is not necessarily an edit-scope room
   // (guest-circulation's is the genkan) -- Finish2()/Finish3() are only
   // meaningful (and only asserted on) when standing somewhere editable;
   // collision/F5/F9/sun are still exercised either way. RoomForCheck is
   // captured now (before any further movement) so the assertions below
   // check the SAME room Finish2() actually touched.
   const bool bEditableHere=IsCurrentRoomEditable(); const FString RoomForCheck=CurrentRoomId;
   if(bEditableHere) Finish2();
   SunHigh(); SaveView(); auto Saved=ReadJSON(SavedViewName());
   Passed &= Saved.IsValid()&&Saved->GetNumberField(TEXT("elevationDeg"))==60;
   if(bEditableHere) Passed &= Saved->GetObjectField(TEXT("roomStates"))->GetObjectField(RoomForCheck)->GetStringField(TEXT("variant"))==TEXT("warm");
   if(bEditableHere) Finish3();
   RestoreView(); Passed &= bReady;
   if(bEditableHere) Passed &= State->GetObjectField(TEXT("roomStates"))->GetObjectField(RoomForCheck)->GetStringField(TEXT("variant"))==TEXT("warm");
   // W07-G2 AC2/AC3: real room-to-room walking + a real openable door
   // blocking when closed and passable when open, exercised generically
   // against representative connections this profile actually has (not
   // necessarily touching the entry room itself -- guest-circulation's own
   // entry room, the genkan, connects to the hall only via a plain
   // leafless archway (door-025, operation 'open'), so restricting this to
   // the entry room would test nothing at all). The character is
   // teleported directly to each side of the chosen door regardless of
   // where it currently stands, so which two rooms the connection actually
   // joins does not matter here. Degenerates to a trivially-true no-op for
   // a zero-door profile (pre-G2 guest-ldk-solo), same "generalises
   // cleanly" contract as every other G2 addition. Uses a real
   // CharacterMovement sweep (SetActorLocation(..., bSweep=true, ...), the
   // same mechanism a walking player's own movement uses) across a SHORT
   // span straddling the door threshold -- not a long-distance sweep from
   // wherever the actor happens to be, which could clip unrelated geometry
   // along the way and give a false result unrelated to the door itself.
   // Both a slide and a swing connection are tried (one representative of
   // each of the two leaf-transform kinds ApplyConditions() applies), not
   // just the first openable connection overall.
   // Points 60cm either side of a connection's own doorway threshold, ON
   // the wall-normal axis (not a room-centroid direction, which can point
   // diagonally through an L-shaped/non-rectangular room instead of
   // straight across the doorway -- LDK's own polygon, e.g., is a 6-vertex
   // L-shape). Which literal direction is SideA's own side is resolved via
   // a real InsideRoomPolygon() containment probe close to the threshold,
   // not a fragile "average of the polygon's vertices" heuristic (which is
   // not even a room's true area centroid, and can land outside an
   // L-shaped polygon entirely, e.g. in the cut-out corner).
   auto ThresholdPositions=[this](const FConnectionInfo* C,const FRoomInfo* SideAInfo)->TArray<FVector> {
    const double MidU=(C->LoCm+C->HiCm)/2.;
    const FVector2D Threshold=C->bHorizontal?FVector2D(MidU,C->AtCm):FVector2D(C->AtCm,MidU);
    const double Z=SideAInfo->FloorCm+88.5;
    const FVector2D Normal=C->bHorizontal?FVector2D(0,1):FVector2D(1,0);
    const FVector2D ProbePlus2D=Threshold+Normal*30.;
    const bool PlusIsSideA=InsideRoomPolygon(C->RoomIds[0],FVector(ProbePlus2D.X,ProbePlus2D.Y,Z),true);
    const FVector2D Direction=PlusIsSideA?Normal:Normal*-1.;
    const FVector2D SideA2D=Threshold+Direction*40., SideB2D=Threshold-Direction*40.;
    return {FVector(SideA2D.X,SideA2D.Y,Z),FVector(SideB2D.X,SideB2D.Y,Z)};
   };
   struct FCirculationCheck {bool BlockedWhenClosed; bool ReachedWhenOpen; bool ToggledOpen; FString MessageAfterOpen;};
   auto TestConnection=[this,&ThresholdPositions](const FConnectionInfo* C)->FCirculationCheck {
    const FRoomInfo* SideAInfo=Rooms.Find(C->RoomIds[0]); const FRoomInfo* SideBInfo=Rooms.Find(C->RoomIds[1]);
    if(!SideAInfo||!SideBInfo) return {false,false,false,TEXT("room not found")}; // profile config names a room this project has no geometry for
    const TArray<FVector> Positions=ThresholdPositions(C,SideAInfo);
    const FVector SideAPos=Positions[0], SideBPos=Positions[1];
    if(GetDoorOpen(C->Id)) {NearestDoorId=C->Id; InteractDoor();} // force a known-closed start
    // UpdateCurrentRoom() only ever searches ONE HOP from whichever room it
    // currently believes it is in (by design -- see its own comment above:
    // real gameplay only ever crosses one threshold per tick). A raw
    // teleport across the room graph (as this synchronous test does, unlike
    // continuous player movement) can land somewhere not directly connected
    // to wherever CurrentRoomId is left over from an earlier check, and it
    // would then never update at all. SideAPos is inside C->RoomIds[0] BY
    // CONSTRUCTION (60cm from the threshold, on that side) -- setting
    // CurrentRoomId directly here (not via UpdateCurrentRoom()) gives every
    // connection's test a known-correct one-hop starting point regardless of
    // which connection ran before it.
    CurrentRoomId=C->RoomIds[0];
    SetActorLocation(SideAPos,false,nullptr,ETeleportType::TeleportPhysics);
    FHitResult ClosedHit; SetActorLocation(SideBPos,true,&ClosedHit,ETeleportType::TeleportPhysics);
    UpdateCurrentRoom(); const bool BlockedWhenClosed=(CurrentRoomId!=C->RoomIds[1]);
    CurrentRoomId=C->RoomIds[0]; SetActorLocation(SideAPos,false,nullptr,ETeleportType::TeleportPhysics);
    NearestDoorId=C->Id; InteractDoor(); // open it
    const bool ToggledOpen=GetDoorOpen(C->Id); FString MessageAfterOpen=Message;
    if(!ToggledOpen) {
     // Diagnostic only (not part of the pass/fail contract): find exactly
     // which actor(s) the player's own capsule overlaps right here, since
     // this is the same position/check InteractDoor()'s own Safe() call
     // just used to reject the toggle -- narrows down whether it is really
     // the door leaf itself (a Blender-side leaf geometry/pivot problem) or
     // something unrelated (furniture placed closer to this doorway than
     // expected).
     TArray<FOverlapResult> Overlaps;
     FCollisionQueryParams Params(SCENE_QUERY_STAT(WalkthroughSmokeDiag),false,this);
     GetWorld()->OverlapMultiByChannel(Overlaps,GetActorLocation(),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(25,87),Params);
     TArray<FString> Labels; for(auto& O:Overlaps) if(O.GetActor()) Labels.AddUnique(O.GetActor()->GetActorLabel());
     const bool InsidePolygon=InsideRoomPolygon(CurrentRoomId,GetActorLocation(),false);
     MessageAfterOpen += FString::Printf(TEXT(" [insideRoomPolygon(margin)=%s overlapping: "),InsidePolygon?TEXT("true"):TEXT("false"))
      +FString::Join(Labels,TEXT(", "))+TEXT("]");
    }
    FHitResult OpenHit; SetActorLocation(SideBPos,true,&OpenHit,ETeleportType::TeleportPhysics);
    UpdateCurrentRoom(); const bool ReachedWhenOpen=(CurrentRoomId==C->RoomIds[1]);
    if(!ReachedWhenOpen) {
     // Diagnostic only: exactly what the open-door sweep actually hit (or,
     // if it landed but still isn't in SideB's room, where it actually is).
     MessageAfterOpen += FString::Printf(TEXT(" [openSweep blockingHit=%s hitActor=%s landed=%s currentRoom=%s]"),
      OpenHit.bBlockingHit?TEXT("true"):TEXT("false"),
      OpenHit.GetActor()?*OpenHit.GetActor()->GetActorLabel():TEXT("none"),
      *GetActorLocation().ToString(),*CurrentRoomId);
    }
    if(ToggledOpen) {NearestDoorId=C->Id; InteractDoor();} // close it back (only if it actually opened)
    CurrentRoomId=C->RoomIds[0]; SetActorLocation(SideAPos,false,nullptr,ETeleportType::TeleportPhysics);
    return {BlockedWhenClosed,ReachedWhenOpen,ToggledOpen,MessageAfterOpen};
   };
   auto Circulation=MakeShared<FJsonObject>();
   bool bCirculationOk=true;
   for(auto Operation:{TEXT("slide"),TEXT("swing")}) {
    const FConnectionInfo* Connection=nullptr;
    for(auto& C:Connections) if(C.bOpenable&&C.Operation==Operation) {Connection=&C; break;}
    auto Entry=MakeShared<FJsonObject>();
    Entry->SetBoolField(TEXT("connectionTested"),Connection!=nullptr);
    if(Connection) {
     Entry->SetStringField(TEXT("connectionId"),Connection->Id);
     auto Result=TestConnection(Connection);
     Entry->SetBoolField(TEXT("blockedWhenClosed"),Result.BlockedWhenClosed);
     Entry->SetBoolField(TEXT("reachedWhenOpen"),Result.ReachedWhenOpen);
     Entry->SetBoolField(TEXT("toggledOpen"),Result.ToggledOpen);
     Entry->SetStringField(TEXT("messageAfterOpen"),Result.MessageAfterOpen);
     bCirculationOk = bCirculationOk && Result.BlockedWhenClosed && Result.ReachedWhenOpen;
    }
    Circulation->SetObjectField(Operation,Entry);
   }
   Passed &= bCirculationOk;
   FString CirculationOut; FJsonSerializer::Serialize(Circulation,TJsonWriterFactory<>::Create(&CirculationOut));
   FFileHelper::SaveStringToFile(CirculationOut,*(FPaths::ProjectSavedDir()/TEXT("walkthrough-smoke-circulation.json")));
   // W07-G2 AC4: a real F5/F9 round trip that also carries room/position/door
   // state -- save while standing in one room with a door OPEN, move away and
   // close it, then confirm F9 restores the SAVED room, position, and door
   // state (not whatever was left when F9 was pressed). Reuses the first
   // openable ('swing', for a leaf that also needs a real rotation restored,
   // not just a translation) connection this profile has, same "degenerates
   // to a no-op for a zero-door profile" contract as the checks above.
   const FConnectionInfo* AC4Connection=nullptr;
   for(auto& C:Connections) if(C.bOpenable&&C.Operation==TEXT("swing")) {AC4Connection=&C; break;}
   bool bAC4Ok=(AC4Connection==nullptr);
   if(AC4Connection) {
    const FRoomInfo* SaveRoomInfo=Rooms.Find(AC4Connection->RoomIds[0]);
    const FRoomInfo* AwayRoomInfo=Rooms.Find(AC4Connection->RoomIds[1]);
    if(SaveRoomInfo&&AwayRoomInfo) {
     // Same threshold-relative, wall-normal-axis points as TestConnection()
     // above (not a room centroid -- see its own comment on why a naive
     // vertex average is unreliable for an L-shaped room like the LDK).
     const TArray<FVector> AC4Positions=ThresholdPositions(AC4Connection,SaveRoomInfo);
     const FVector SavePos=AC4Positions[0], AwayPos=AC4Positions[1];
     if(GetDoorOpen(AC4Connection->Id)) {NearestDoorId=AC4Connection->Id; InteractDoor();} // known-closed start
     CurrentRoomId=AC4Connection->RoomIds[0];
     SetActorLocation(SavePos,false,nullptr,ETeleportType::TeleportPhysics);
     NearestDoorId=AC4Connection->Id; InteractDoor(); // open it before saving
     const bool OpenedBeforeSave=GetDoorOpen(AC4Connection->Id);
     SaveView(); const bool SaveOk=bReady;
     CurrentRoomId=AC4Connection->RoomIds[1];
     SetActorLocation(AwayPos,false,nullptr,ETeleportType::TeleportPhysics);
     NearestDoorId=AC4Connection->Id; InteractDoor(); // close it again -- must NOT be what F9 restores
     const bool ClosedAfterSave=!GetDoorOpen(AC4Connection->Id);
     RestoreView();
     const bool RoomRestored=(CurrentRoomId==AC4Connection->RoomIds[0]);
     const bool DoorRestoredOpen=GetDoorOpen(AC4Connection->Id);
     bAC4Ok=OpenedBeforeSave&&SaveOk&&ClosedAfterSave&&bReady&&RoomRestored&&DoorRestoredOpen;
     auto AC4Result=MakeShared<FJsonObject>();
     AC4Result->SetStringField(TEXT("connectionId"),AC4Connection->Id);
     AC4Result->SetBoolField(TEXT("openedBeforeSave"),OpenedBeforeSave);
     AC4Result->SetBoolField(TEXT("closedAfterSave"),ClosedAfterSave);
     AC4Result->SetBoolField(TEXT("roomRestored"),RoomRestored);
     AC4Result->SetBoolField(TEXT("doorRestoredOpen"),DoorRestoredOpen);
     AC4Result->SetBoolField(TEXT("passed"),bAC4Ok);
     FString AC4Out; FJsonSerializer::Serialize(AC4Result,TJsonWriterFactory<>::Create(&AC4Out));
     FFileHelper::SaveStringToFile(AC4Out,*(FPaths::ProjectSavedDir()/TEXT("walkthrough-smoke-ac4.json")));
     if(GetDoorOpen(AC4Connection->Id)) {NearestDoorId=AC4Connection->Id; InteractDoor();} // leave closed for the final RestoreView() below
    }
   }
   Passed &= bAC4Ok;
   RestoreView(); // back to the saved viewpoint/room -- do not leave the smoke test standing wherever the above left off
  }
  FFileHelper::SaveStringToFile(Passed?TEXT("PASS"):TEXT("FAIL"),*(FPaths::ProjectSavedDir()/TEXT("walkthrough-smoke.txt")));
  FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("walkthrough-smoke.png"),false,false);
 }
 if(bSmokeDone&&GetWorld()->GetTimeSeconds()>6) {FPlatformMisc::RequestExit(false);return;}
 if(!PC||!bReady||PC->bShowMouseCursor) return;
 float MX,MY; PC->GetInputMouseDelta(MX,MY); AddControllerYawInput(MX*.5); AddControllerPitchInput(-MY*.5);
 auto Rotation=FRotator(0,PC->GetControlRotation().Yaw,0); auto Forward=Rotation.Vector(); auto Right=FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y);
 FVector Direction=Forward*((PC->IsInputKeyDown(EKeys::W)?1:0)-(PC->IsInputKeyDown(EKeys::S)?1:0))+Right*((PC->IsInputKeyDown(EKeys::D)?1:0)-(PC->IsInputKeyDown(EKeys::A)?1:0));
 if(!Direction.IsNearlyZero()) AddMovementInput(Direction.GetSafeNormal());
}
AWalkthroughGameMode::AWalkthroughGameMode(){DefaultPawnClass=AWalkthroughCharacter::StaticClass();HUDClass=AWalkthroughHUD::StaticClass();}
void AWalkthroughHUD::DrawHUD(){
 Super::DrawHUD();
 DrawRect(FLinearColor(0,0,0,.65),12,12,820,186);
 DrawText(TEXT("WASD：歩行　｜　マウス：視点　｜　Tab：カーソル解放　｜　F5：保存　｜　F9：復元　｜　E：扉の開閉"),FLinearColor::White,24,22);
 DrawText(TEXT("1/2/3：仕上げ切替（対象室のみ）　｜　4/5：太陽高度30/60度　｜　目線高さ1.60m　｜　採光は仮条件です"),FLinearColor::White,24,44);
 if(auto P=Cast<AWalkthroughCharacter>(GetOwningPawn())) {
  // W07-G2: which room the player is standing in, and whether the finish
  // keys currently do anything here at all (spec section 3: "ホール等の
  // 未編集室ではその旨を表示").
  DrawText(TEXT("現在の部屋：")+P->CurrentRoomLabel(),FLinearColor::White,24,66);
  const FString Variant=P->CurrentVariantLabel();
  DrawText(Variant.IsEmpty()?FString(TEXT("現在の仕上げ：－（この部屋は編集対象外）")):(TEXT("現在の仕上げ：")+Variant),FLinearColor::White,24,88);
  // W05:日時由来か手動角度かをHUDで区別する。
  DrawText(TEXT("太陽条件：")+P->CurrentSolarLabel(),FLinearColor::White,24,110);
  // W06: 昼夜モードと、明るさ・色温度が仮仕様であることを常設表示する。
  DrawText(TEXT("照明：")+P->CurrentLightingLabel(),FLinearColor::White,24,132);
  // W07-G2: only shown when actually near and facing an openable door.
  const FString DoorPrompt=P->DoorPromptLabel();
  if(!DoorPrompt.IsEmpty()) DrawText(DoorPrompt,FLinearColor::Green,24,154);
  DrawText(P->Message,FLinearColor::Yellow,24,176);
 }
}
int32 UWalkthroughLibrary::Prepare(UWorld* World) {
 int32 Count=0;
 for(TActorIterator<AActor> It(World);It;++It) {
#if WITH_EDITOR
  FString Label=It->GetActorLabel(); It->Tags.AddUnique(FName(TEXT("Ryuka:")+Label));
  if(auto Mesh=Cast<AStaticMeshActor>(*It)) {
   auto C=Mesh->GetStaticMeshComponent(); bool Block=!Label.StartsWith(TEXT("decoration_"))&&!Label.StartsWith(TEXT("Ground_"));
   if(Block&&C->GetStaticMesh()&&C->GetStaticMesh()->GetBodySetup()) {
    auto Body=C->GetStaticMesh()->GetBodySetup(); Body->CollisionTraceFlag=CTF_UseComplexAsSimple;
    C->GetStaticMesh()->MarkPackageDirty(); C->SetCollisionProfileName(TEXT("BlockAll")); C->RecreatePhysicsState(); Count++;
   } else C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
  }
#endif
 }
 return Count;
}
