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
bool AWalkthroughCharacter::Safe(const FVector& P) const {
 // Interior and 25cm clearance from the room boundary; handles concave outlines.
 bool Inside=false; FVector2D Q(P.X,P.Y);
 for(int32 I=0,J=Room.Num()-1;I<Room.Num();J=I++) {
  const FVector2D A=Room[I],B=Room[J];
  if((A.Y>Q.Y)!=(B.Y>Q.Y) && Q.X<(B.X-A.X)*(Q.Y-A.Y)/(B.Y-A.Y)+A.X) Inside=!Inside;
  const FVector2D D=B-A;
  const float T=FMath::Clamp(FVector2D::DotProduct(Q-A,D)/FMath::Max(D.SizeSquared(),.001),0.,1.);
  if((Q-(A+T*D)).Size()<26) return false;
 }
 if(!Inside) return false;
 FCollisionQueryParams Params(SCENE_QUERY_STAT(WalkthroughSpawn),false,this);
 return !GetWorld()->OverlapBlockingTestByChannel(P,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(25,87),Params);
}
void AWalkthroughCharacter::BeginPlay() {
 Super::BeginPlay();
 auto Config=ReadJSON(TEXT("walkthrough.json"));
 if(!Config.IsValid()) {Message=TEXT("Missing walkthrough configuration"); GetCharacterMovement()->DisableMovement(); return;}
 Floor=Config->GetNumberField(TEXT("floorCm"));
 for(auto Value:Config->GetArrayField(TEXT("polygonCm"))) {
  auto P=Value->AsArray(); Room.Add(FVector2D(P[0]->AsNumber(),P[1]->AsNumber()));
 }
 GetCharacterMovement()->DisableMovement();
}
bool AWalkthroughCharacter::Restore(const TSharedPtr<FJsonObject>& Candidate) {
 if(!Candidate.IsValid()||Candidate->GetStringField(TEXT("roomId"))!=ReadJSON(TEXT("walkthrough.json"))->GetStringField(TEXT("roomId"))) return false;
 const TSharedPtr<FJsonObject>* Camera; FVector P,R;
 if(!Candidate->TryGetObjectField(TEXT("camera"),Camera)||!VectorField(*Camera,TEXT("locationCm"),P)||!VectorField(*Camera,TEXT("rotationDeg"),R)) return false;
 P.Z=Floor+88.5;
 bool Adjusted=false;
 if(!Safe(P)) {
  double Best=TNumericLimits<double>::Max(); FVector Found;
  for(int32 X=0;X<100;X++) for(int32 Y=0;Y<100;Y++) {
   FVector Test(Room[0].X-500+X*15,Room[0].Y-500+Y*15,P.Z);
   double Distance=FVector::DistSquared2D(P,Test);
   if(Distance<Best&&Safe(Test)) {Best=Distance; Found=Test;}
  }
  if(Best==TNumericLimits<double>::Max()) {Message=TEXT("No safe start position. Review furniture layout.");return false;}
  P=Found; Adjusted=true;
 }
 auto Previous=State; State=Candidate;
 if(!ApplyConditions()) {State=Previous; return false;}
 SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);
 GetCharacterMovement()->StopMovementImmediately(); GetCharacterMovement()->SetMovementMode(MOVE_Walking);
 Controller->SetControlRotation(FRotator(FMath::Clamp(R.X,-80.,80.),R.Y,0));
 bReady=true; Message=Adjusted?TEXT("Moved to nearest clear position"):TEXT("View restored"); return true;
}
void AWalkthroughCharacter::RestoreView() {
 const FString Saved=FPaths::ProjectDir()/SavedViewName(), Base=FPaths::ProjectDir()/TEXT("study-state.json");
 const bool Newer=IFileManager::Get().GetTimeStamp(*Saved)>IFileManager::Get().GetTimeStamp(*Base);
 if(!(Newer&&Restore(ReadJSON(SavedViewName())))&&!Restore(ReadJSON(TEXT("study-state.json")))) {
  bReady=false; GetCharacterMovement()->DisableMovement(); Message=TEXT("Cannot restore a valid view");
 }
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
void AWalkthroughCharacter::SetFinish(const FString& Name) {
 if(!bReady) return; FString Old=State->GetStringField(TEXT("variant")); State->SetStringField(TEXT("variant"),Name);
 if(!ApplyConditions()) {State->SetStringField(TEXT("variant"),Old);Message=TEXT("Finish unavailable");} else Message=Name;
}
void AWalkthroughCharacter::SetSun(float Elevation) {
 if(!bReady) return; State->SetNumberField(TEXT("elevationDeg"),Elevation); State->RemoveField(TEXT("solar")); ApplyConditions(); Message=TEXT("Manual sun angle (not calibrated)");
}
void AWalkthroughCharacter::Finish1(){SetFinish(TEXT("natural"));} void AWalkthroughCharacter::Finish2(){SetFinish(TEXT("warm"));}
void AWalkthroughCharacter::Finish3(){SetFinish(TEXT("reference"));} void AWalkthroughCharacter::SunLow(){SetSun(30);} void AWalkthroughCharacter::SunHigh(){SetSun(60);}
void AWalkthroughCharacter::SaveView() {
 if(!bReady) return;
 auto Camera=MakeShared<FJsonObject>(); Camera->SetArrayField(TEXT("locationCm"),Numbers(Eye->GetComponentLocation()));
 auto R=Controller->GetControlRotation(); Camera->SetArrayField(TEXT("rotationDeg"),Numbers(FVector(R.Pitch,R.Yaw,0)));
 Camera->SetNumberField(TEXT("lensMm"),18./tan(FMath::DegreesToRadians(Eye->FieldOfView/2)));
 State->SetObjectField(TEXT("camera"),Camera);
 FString Text; FJsonSerializer::Serialize(State.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
 FString Path=FPaths::ProjectDir()/SavedViewName(),Tmp=Path+TEXT(".tmp");
 if(FFileHelper::SaveStringToFile(Text,*Tmp,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)&&IFileManager::Get().Move(*Path,*Tmp,true,true)==COPY_OK) Message=TEXT("View and conditions saved");
 else Message=TEXT("Save failed");
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
 if(PC&&!bInitialized) {bInitialized=true; RestoreView(); PC->bShowMouseCursor=false; PC->SetInputMode(FInputModeGameOnly());}
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
 FVector Next=GetActorLocation()+Direction.GetSafeNormal()*120*FMath::Min(Delta,.1f);
 if(!Direction.IsNearlyZero()&&Safe(Next)) AddMovementInput(Direction.GetSafeNormal());
}
AWalkthroughGameMode::AWalkthroughGameMode(){DefaultPawnClass=AWalkthroughCharacter::StaticClass();HUDClass=AWalkthroughHUD::StaticClass();}
void AWalkthroughHUD::DrawHUD(){Super::DrawHUD();DrawRect(FLinearColor(0,0,0,.65),12,12,760,76);DrawText(TEXT("WASD: walk | Mouse: look | Tab: release cursor | F5: save | F9: restore"),FLinearColor::White,24,22);DrawText(TEXT("1/2/3: finishes | 4/5: sun 30/60 degrees | Eye height 1.60m | provisional daylight"),FLinearColor::White,24,44);if(auto P=Cast<AWalkthroughCharacter>(GetOwningPawn()))DrawText(P->Message,FLinearColor::Yellow,24,66);}
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
