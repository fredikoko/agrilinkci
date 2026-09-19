[app]
# Nom affiché de l'application
title = AgriLink CI
package.name = agrilinkci
package.domain = ci.agrilink
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1.0
requirements = python3,kivy,requests,pyjnius,certifi,urllib3
orientation = portrait
fullscreen = 0

# Remplacer l'URL locale utilisée par défaut dans main.py par l'URL publique du backend avant compilation.

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.api = 33
android.minapi = 23
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,POST_NOTIFICATIONS,ACCESS_NETWORK_STATE,ACCESS_COARSE_LOCATION,ACCESS_FINE_LOCATION
