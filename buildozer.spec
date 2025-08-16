[app]
# Основные данные о приложении
title = Narnilla Dice Roller
package.name = narnilladice
package.domain = org.example
source.dir = .
source.include_exts = py,png
version = 1.0
requirements = python3==3.11,kivy==2.3.1
icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 0

# Android специфичные параметры
android.sdk = 33
android.ndk = 25b
android.api = 33
android.minapi = 21
android.build_tools_version = 33.0.2
android.ndk_path = ./ndk
android.sdk_path = ./sdk

[buildozer]
log_level = 2
warn_on_root = 1
