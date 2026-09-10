@echo off
rem ============================================================
rem  ゲスト内覧ランチャー（W08-G）
rem  このファイルをダブルクリックすると起動します。
rem  起動時の作業フォルダに依存せず、このワークツリーを基準に
rem  パスを解決します。空白・日本語を含むパスでも動作します。
rem ============================================================
setlocal
cd /d "%~dp0"

rem Python を探す（py ランチャー優先、無ければ python）
set "PYEXE="
where py >nul 2>nul && set "PYEXE=py -3"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE (
  echo Python が見つかりません。Python 3 を導入してください。
  pause
  exit /b 1
)

%PYEXE% -X utf8 "%~dp0scripts\guest_launcher\__main__.py" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo ランチャーが終了コード %RC% で終了しました。build\launcher\logs\ を確認してください。
  pause
)
endlocal & exit /b %RC%
