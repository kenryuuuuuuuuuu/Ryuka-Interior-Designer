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
#include "Materials/MaterialInterface.h"
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
 return FParse::Param(FCommandLine::Get(),TEXT("RyukaSmoke")) ? TEXT("Saved/walkthrough-smoke-state.json") : TEXT("Saved/walkthrough-state.json");
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
AWalkthroughCharacter::AWalkthroughCharacter() {
 PrimaryActorTick.bCanEverTick=true;
 GetCapsuleComponent()->InitCapsuleSize(25,88);
 Eye=CreateDefaultSubobject<UCameraComponent>(TEXT("Eye")); Eye->SetupAttachment(GetCapsuleComponent());
 Eye->SetRelativeLocation(FVector(0,0,72)); Eye->bUsePawnControlRotation=true; Eye->FieldOfView=80;
 GetCharacterMovement()->MaxWalkSpeed=120; GetCharacterMovement()->MaxStepHeight=2;
 GetCharacterMovement()->bCanWalkOffLedges=false;
 bUseControllerRotationYaw=true;
}
bool AWalkthroughCharacter::InsideRoom(const FVector& P) const {
 // Interior and 25cm clearance from the room boundary; handles concave outlines.
 // This is the invisible boundary (openings/doorways have no physical wall),
 // kept separate from furniture/wall collision so Tick() can enforce it after
 // the normal CharacterMovement sweep instead of blocking movement input.
 bool Inside=false; FVector2D Q(P.X,P.Y);
 for(int32 I=0,J=Room.Num()-1;I<Room.Num();J=I++) {
  const FVector2D A=Room[I],B=Room[J];
  if((A.Y>Q.Y)!=(B.Y>Q.Y) && Q.X<(B.X-A.X)*(Q.Y-A.Y)/(B.Y-A.Y)+A.X) Inside=!Inside;
  const FVector2D D=B-A;
  const float T=FMath::Clamp(FVector2D::DotProduct(Q-A,D)/FMath::Max(D.SizeSquared(),.001),0.,1.);
  if((Q-(A+T*D)).Size()<26) return false;
 }
 return Inside;
}
bool AWalkthroughCharacter::Safe(const FVector& P) const {
 if(!InsideRoom(P)) return false;
 FCollisionQueryParams Params(SCENE_QUERY_STAT(WalkthroughSpawn),false,this);
 return !GetWorld()->OverlapBlockingTestByChannel(P,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(25,87),Params);
}
void AWalkthroughCharacter::BeginPlay() {
 Super::BeginPlay();
 auto Config=ReadJSON(TEXT("walkthrough.json"));
 if(!Config.IsValid()) {Message=TEXT("内覧の設定が見つかりません"); GetCharacterMovement()->DisableMovement(); return;}
 Floor=Config->GetNumberField(TEXT("floorCm"));
 for(auto Value:Config->GetArrayField(TEXT("polygonCm"))) {
  auto P=Value->AsArray(); Room.Add(FVector2D(P[0]->AsNumber(),P[1]->AsNumber()));
 }
 GetCharacterMovement()->DisableMovement();
}
bool AWalkthroughCharacter::Restore(const TSharedPtr<FJsonObject>& Candidate) {
 FString Schema;
 if(!Candidate.IsValid()||!Candidate->TryGetStringField(TEXT("schemaVersion"),Schema)||Schema!=TEXT("1.0.0")) {
  Message=TEXT("保存データの形式（バージョン）が無効です"); return false;
 }
 FString RoomId,ExpectedRoomId; auto WalkConfig=ReadJSON(TEXT("walkthrough.json"));
 if(!Candidate->TryGetStringField(TEXT("roomId"),RoomId)||!WalkConfig.IsValid()||
 !WalkConfig->TryGetStringField(TEXT("roomId"),ExpectedRoomId)||RoomId!=ExpectedRoomId) {
  Message=TEXT("別の部屋の保存データです"); return false;
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
 P.Z=Floor+88.5;
 bool Adjusted=false;
 if(!Safe(P)) {
  double Best=TNumericLimits<double>::Max(); FVector Found;
  for(int32 X=0;X<100;X++) for(int32 Y=0;Y<100;Y++) {
   FVector Test(Room[0].X-500+X*15,Room[0].Y-500+Y*15,P.Z);
   double Distance=FVector::DistSquared2D(P,Test);
   if(Distance<Best&&Safe(Test)) {Best=Distance; Found=Test;}
  }
  if(Best==TNumericLimits<double>::Max()) {Message=TEXT("安全な開始位置がありません。家具配置を確認してください。");return false;}
  P=Found; Adjusted=true;
 }
 auto Previous=State; State=Candidate;
 if(!ApplyConditions()) {State=Previous; Message=TEXT("保存データの仕上げ・太陽条件を適用できません"); return false;}
 SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);
 GetCharacterMovement()->StopMovementImmediately(); GetCharacterMovement()->SetMovementMode(MOVE_Walking);
 Controller->SetControlRotation(FRotator(FMath::Clamp(R.X,-80.,80.),R.Y,0));
 Eye->FieldOfView=FMath::RadiansToDegrees(2.*atan(18./LensMm));
 LastSafeLocation=P;
 bReady=true; Message=Adjusted?TEXT("空いている最も近い位置へ移動しました"):TEXT("視点を復元しました"); return true;
}
void AWalkthroughCharacter::RestoreView() {
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
 auto Bindings=ReadJSON(TEXT("study-bindings.json")); if(!Bindings.IsValid()||!State.IsValid()) return false;
 FString Variant; double Az,El,Lux,EV;
 if(!State->TryGetStringField(TEXT("variant"),Variant)||!State->TryGetNumberField(TEXT("azimuthDeg"),Az)||
 !State->TryGetNumberField(TEXT("elevationDeg"),El)||!State->TryGetNumberField(TEXT("sunLux"),Lux)||!State->TryGetNumberField(TEXT("exposureEV100"),EV)) return false;
 if(!FMath::IsFinite(Az)||!FMath::IsFinite(El)||!FMath::IsFinite(Lux)||!FMath::IsFinite(EV)||Az<0||Az>360||El<1||El>89||Lux<1||Lux>150000||EV< -5||EV>20) return false;
 TMap<FString,AActor*> Actors;
 for(TActorIterator<AActor> It(GetWorld());It;++It) for(auto Tag:It->Tags) if(Tag.ToString().StartsWith(TEXT("Ryuka:"))) Actors.Add(Tag.ToString().Mid(6),*It);
 struct Assignment {UStaticMeshComponent* Component; int32 Slot; UMaterialInterface* Material;}; TArray<Assignment> Plan;
 for(auto& Entry:Bindings->Values) {
  auto Actor=Cast<AStaticMeshActor>(Actors.FindRef(FString(*Entry.Key))); if(!Actor) return false;
  for(auto& Slot:Entry.Value->AsObject()->Values) {
   auto Material=LoadObject<UMaterialInterface>(nullptr,*(TEXT("/Game/Generated/Finishes/M_")+Variant+TEXT("_")+Slot.Value->AsString()));
   int32 Index=FCString::Atoi(*Slot.Key); auto Component=Actor->GetStaticMeshComponent();
   if(!Material||Index<0||Index>=Component->GetNumMaterials()) return false;
   Plan.Add({Component,Index,Material});
  }
 }
 auto Sun=Cast<ADirectionalLight>(Actors.FindRef(TEXT("Sun_manual_angle")));
 auto Post=Cast<APostProcessVolume>(Actors.FindRef(TEXT("Fixed_exposure"))); if(!Sun||!Post) return false;
 for(auto& Item:Plan) Item.Component->SetMaterial(Item.Slot,Item.Material);
 Az=FMath::DegreesToRadians(Az); El=FMath::DegreesToRadians(El);
 Sun->SetActorRotation(FVector(-sin(Az)*cos(El),cos(Az)*cos(El),-sin(El)).Rotation());
 Sun->GetLightComponent()->SetIntensity(Lux);
 Post->Settings.AutoExposureMinBrightness=EV; Post->Settings.AutoExposureMaxBrightness=EV;
 return true;
}
void AWalkthroughCharacter::SetFinish(const FString& Name,const FString& Label) {
 if(!bReady) return; FString Old=State->GetStringField(TEXT("variant")); State->SetStringField(TEXT("variant"),Name);
 if(!ApplyConditions()) {State->SetStringField(TEXT("variant"),Old);Message=TEXT("この仕上げは利用できません");} else Message=Label;
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
// Labels match study_controls.py's register_menu() so the walkthrough and the
// editor menu describe the same variants identically.
void AWalkthroughCharacter::Finish1(){SetFinish(TEXT("natural"),TEXT("白壁・ナチュラルオーク"));} void AWalkthroughCharacter::Finish2(){SetFinish(TEXT("warm"),TEXT("グレージュ・ウォルナット"));}
void AWalkthroughCharacter::Finish3(){SetFinish(TEXT("reference"),TEXT("石調の床・木板天井"));} void AWalkthroughCharacter::SunLow(){SetSun(30);} void AWalkthroughCharacter::SunHigh(){SetSun(60);}
FString AWalkthroughCharacter::CurrentVariantLabel() const {
 if(!bReady||!State.IsValid()) return FString();
 FString Variant; if(!State->TryGetStringField(TEXT("variant"),Variant)) return FString();
 if(Variant==TEXT("natural")) return TEXT("白壁・ナチュラルオーク");
 if(Variant==TEXT("warm")) return TEXT("グレージュ・ウォルナット");
 if(Variant==TEXT("reference")) return TEXT("石調の床・木板天井");
 return Variant;
}
void AWalkthroughCharacter::SaveView() {
 if(!bReady) return;
 auto Camera=MakeShared<FJsonObject>(); Camera->SetArrayField(TEXT("locationCm"),Numbers(Eye->GetComponentLocation()));
 auto R=Controller->GetControlRotation(); Camera->SetArrayField(TEXT("rotationDeg"),Numbers(FVector(R.Pitch,R.Yaw,0)));
 Camera->SetNumberField(TEXT("lensMm"),18./tan(FMath::DegreesToRadians(Eye->FieldOfView/2)));
 State->SetObjectField(TEXT("camera"),Camera);
 FString Text; FJsonSerializer::Serialize(State.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
 const FString Path=FPaths::ProjectDir()/SavedViewName(),Tmp=Path+TEXT(".tmp"),Backup=Path+TEXT(".bak");
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
   if(IFileManager::Get().Move(*Path,*Tmp,true,true)) {
    bSuccess=true;
    IFileManager::Get().Delete(*Backup,false,true,true);
   } else {
    IFileManager::Get().Move(*Path,*Backup,true,true); // restore the previous save
   }
  }
  // If the rename-to-Backup step itself failed, Path was never touched and
  // the previous save is intact; bSuccess stays false either way here.
 }
 Message=bSuccess?TEXT("視点と条件を保存しました"):TEXT("保存に失敗しました");
}
void AWalkthroughCharacter::ToggleMouse() {auto PC=Cast<APlayerController>(Controller); PC->bShowMouseCursor=!PC->bShowMouseCursor; if(PC->bShowMouseCursor) PC->SetInputMode(FInputModeGameAndUI()); else PC->SetInputMode(FInputModeGameOnly());}
void AWalkthroughCharacter::SetupPlayerInputComponent(UInputComponent* I) {
 Super::SetupPlayerInputComponent(I);
 I->BindKey(EKeys::One,IE_Pressed,this,&AWalkthroughCharacter::Finish1); I->BindKey(EKeys::Two,IE_Pressed,this,&AWalkthroughCharacter::Finish2); I->BindKey(EKeys::Three,IE_Pressed,this,&AWalkthroughCharacter::Finish3);
 I->BindKey(EKeys::Four,IE_Pressed,this,&AWalkthroughCharacter::SunLow); I->BindKey(EKeys::Five,IE_Pressed,this,&AWalkthroughCharacter::SunHigh);
 I->BindKey(EKeys::F5,IE_Pressed,this,&AWalkthroughCharacter::SaveView); I->BindKey(EKeys::F9,IE_Pressed,this,&AWalkthroughCharacter::RestoreView); I->BindKey(EKeys::Tab,IE_Pressed,this,&AWalkthroughCharacter::ToggleMouse);
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
   // actor unsafe, LastSafeLocation keeps its last known-Safe value and the
   // actor stays wherever the second sweep stopped (a sweep endpoint, never
   // a location reached by ignoring collision) for the next Tick to retry.
   if(Safe(Landed)) LastSafeLocation=Landed;
  } else LastSafeLocation=Current;
 }
 if(FParse::Param(FCommandLine::Get(),TEXT("RyukaSmoke"))&&GetWorld()->GetTimeSeconds()>3&&!bSmokeDone) {
  bSmokeDone=true; bool Passed=bReady;
  if(bReady) {
   const FVector Start=GetActorLocation(); FHitResult Hit;
   SetActorLocation(Start+FVector(2000,0,0),true,&Hit);
   Passed &= Hit.bBlockingHit && FVector::Dist2D(Start,GetActorLocation())<1900;
   RestoreView(); Finish2(); SunHigh(); SaveView(); auto Saved=ReadJSON(SavedViewName());
   Passed &= Saved.IsValid()&&Saved->GetStringField(TEXT("variant"))==TEXT("warm")&&Saved->GetNumberField(TEXT("elevationDeg"))==60;
   Finish3(); RestoreView(); Passed &= bReady&&State->GetStringField(TEXT("variant"))==TEXT("warm");
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
 DrawRect(FLinearColor(0,0,0,.65),12,12,820,98);
 DrawText(TEXT("WASD：歩行　｜　マウス：視点　｜　Tab：カーソル解放　｜　F5：保存　｜　F9：復元"),FLinearColor::White,24,22);
 DrawText(TEXT("1/2/3：仕上げ切替　｜　4/5：太陽高度30/60度　｜　目線高さ1.60m　｜　採光は仮条件です"),FLinearColor::White,24,44);
 if(auto P=Cast<AWalkthroughCharacter>(GetOwningPawn())) {
  const FString Variant=P->CurrentVariantLabel();
  DrawText(Variant.IsEmpty()?FString(TEXT("現在の仕上げ：－")):(TEXT("現在の仕上げ：")+Variant),FLinearColor::White,24,66);
  DrawText(P->Message,FLinearColor::Yellow,24,88);
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
