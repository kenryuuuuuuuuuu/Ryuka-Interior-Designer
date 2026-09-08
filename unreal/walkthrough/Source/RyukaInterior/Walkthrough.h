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
 void SaveView(); void RestoreView(); void ToggleMouse();
 FString CurrentVariantLabel() const;
 FString Message;
 bool bReady=false;
 bool bInitialized=false;
 bool bSmokeDone=false;
private:
 UPROPERTY() class UCameraComponent* Eye;
 TSharedPtr<class FJsonObject> State;
 TArray<FVector2D> Room;
 float Floor=0;
 FVector LastSafeLocation=FVector::ZeroVector;
 void SetFinish(const FString& Name,const FString& Label);
 void SetSun(float Elevation);
 bool ApplyConditions();
 bool InsideRoom(const FVector& Position) const;
 bool Safe(const FVector& Position) const;
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
