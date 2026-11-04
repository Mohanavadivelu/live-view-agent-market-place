plugins {
    id("com.android.application")
}

android {
    namespace = "dev.liveview.testbench"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "dev.liveview.testbench"
        minSdk = 30
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
