"""
Windows Privacy Tweaks Engine
Handles all registry, service, and scheduled task modifications.
"""

import winreg
import subprocess
import ctypes
import os

# --------------------------------------------------
# Registry helpers
# --------------------------------------------------

def _set_reg(hive, path, name, value, reg_type=winreg.REG_DWORD):
    """Set a registry value, creating the key path if needed."""
    try:
        key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.SetValueEx(key, name, 0, reg_type, value)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def _get_reg(hive, path, name):
    """Read a registry value. Returns None if not found."""
    try:
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return val
    except OSError:
        return None


def _del_reg(hive, path, name):
    """Delete a registry value."""
    try:
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def _run(cmd, shell=True):
    """Run a shell command silently."""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def is_admin():
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# --------------------------------------------------
# Tweak definitions
# Each tweak is a dict with:
#   name, description, category, apply(), check()
# apply() -> bool (success)
# check() -> bool (True = already privacy-friendly)
# --------------------------------------------------

TWEAKS = []


def tweak(name, description, category):
    """Decorator to register a tweak."""
    def decorator(cls):
        TWEAKS.append({
            "name": name,
            "description": description,
            "category": category,
            "apply": cls.apply,
            "check": cls.check,
        })
        return cls
    return decorator


# --------------------------------------------------
# Telemetry & Diagnostics
# --------------------------------------------------

@tweak("Disable Telemetry", "Sets telemetry level to 0 (Security/Off)", "Telemetry & Diagnostics")
class DisableTelemetry:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                       "AllowTelemetry", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection",
                       "AllowTelemetry", 0)
        r3 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                       "MaxTelemetryAllowed", 0)
        return r1 and r2 and r3

    @staticmethod
    def check():
        v = _get_reg(winreg.HKEY_LOCAL_MACHINE,
                     r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                     "AllowTelemetry")
        return v == 0


@tweak("Disable Diagnostic Data", "Prevents sending diagnostic data to Microsoft", "Telemetry & Diagnostics")
class DisableDiagnosticData:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\Diagnostics\DiagTrack",
                       "ShowedToastAtLevel", 1)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                       "AllowDeviceNameInTelemetry", 0)
        r3 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                       "DoNotShowFeedbackNotifications", 1)
        return r1 and r2 and r3

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                        "DoNotShowFeedbackNotifications") == 1


@tweak("Disable DiagTrack Service", "Stops and disables Connected User Experiences and Telemetry service", "Telemetry & Diagnostics")
class DisableDiagTrack:
    @staticmethod
    def apply():
        _run("sc stop DiagTrack")
        return _run("sc config DiagTrack start= disabled")

    @staticmethod
    def check():
        r = subprocess.run("sc qc DiagTrack", shell=True, capture_output=True, text=True)
        return "DISABLED" in r.stdout.upper()


@tweak("Disable dmwappushservice", "Stops WAP Push Message Routing Service used for telemetry", "Telemetry & Diagnostics")
class DisableDmwappush:
    @staticmethod
    def apply():
        _run("sc stop dmwappushservice")
        return _run("sc config dmwappushservice start= disabled")

    @staticmethod
    def check():
        r = subprocess.run("sc qc dmwappushservice", shell=True, capture_output=True, text=True)
        return "DISABLED" in r.stdout.upper()


@tweak("Disable Error Reporting", "Disables Windows Error Reporting", "Telemetry & Diagnostics")
class DisableErrorReporting:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\Windows\Windows Error Reporting",
                       "Disabled", 1)
        _run("sc stop WerSvc")
        r2 = _run("sc config WerSvc start= disabled")
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\Windows\Windows Error Reporting",
                        "Disabled") == 1


@tweak("Disable CEIP", "Disables Customer Experience Improvement Program", "Telemetry & Diagnostics")
class DisableCEIP:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\SQMClient\Windows",
                       "CEIPEnable", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\AppV\CEIP",
                       "CEIPEnable", 0)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\SQMClient\Windows",
                        "CEIPEnable") == 0


@tweak("Disable Application Telemetry", "Disables Application Compatibility telemetry engine", "Telemetry & Diagnostics")
class DisableAppTelemetry:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppCompat",
                        "AITEnable", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppCompat",
                        "AITEnable") == 0


# --------------------------------------------------
# Advertising & Tracking
# --------------------------------------------------

@tweak("Disable Advertising ID", "Prevents apps from using your advertising ID", "Advertising & Tracking")
class DisableAdID:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                       "Enabled", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo",
                       "DisabledByGroupPolicy", 1)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                        "Enabled") == 0


@tweak("Disable Tailored Experiences", "Stops Microsoft from using diagnostic data for personalized tips/ads", "Advertising & Tracking")
class DisableTailoredExperiences:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                       "DisableTailoredExperiencesWithDiagnosticData", 1)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
                       "TailoredExperiencesWithDiagnosticDataEnabled", 0)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                        "DisableTailoredExperiencesWithDiagnosticData") == 1


@tweak("Disable Suggested Content in Settings", "Removes suggested content from the Settings app", "Advertising & Tracking")
class DisableSuggestedContent:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        r1 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SubscribedContent-338393Enabled", 0)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SubscribedContent-353694Enabled", 0)
        r3 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SubscribedContent-353696Enabled", 0)
        return r1 and r2 and r3

    @staticmethod
    def check():
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        return _get_reg(winreg.HKEY_CURRENT_USER, base, "SubscribedContent-338393Enabled") == 0


@tweak("Disable Start Menu Suggestions", "Removes app suggestions and ads from Start Menu", "Advertising & Tracking")
class DisableStartSuggestions:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        r1 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SystemPaneSuggestionsEnabled", 0)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SoftLandingEnabled", 0)
        r3 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SubscribedContent-310093Enabled", 0)
        r4 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SubscribedContent-338388Enabled", 0)
        return r1 and r2 and r3 and r4

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                        "SystemPaneSuggestionsEnabled") == 0


@tweak("Disable Pre-installed App Delivery", "Stops silent installation of promoted apps", "Advertising & Tracking")
class DisableSilentApps:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        r1 = _set_reg(winreg.HKEY_CURRENT_USER, base, "SilentInstalledAppsEnabled", 0)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER, base, "ContentDeliveryAllowed", 0)
        r3 = _set_reg(winreg.HKEY_CURRENT_USER, base, "OemPreInstalledAppsEnabled", 0)
        r4 = _set_reg(winreg.HKEY_CURRENT_USER, base, "PreInstalledAppsEnabled", 0)
        return r1 and r2 and r3 and r4

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                        "SilentInstalledAppsEnabled") == 0


# --------------------------------------------------
# Cortana & Search
# --------------------------------------------------

@tweak("Disable Cortana", "Disables Cortana assistant", "Cortana & Search")
class DisableCortana:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                       "AllowCortana", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                       "AllowCortanaAboveLock", 0)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                        "AllowCortana") == 0


@tweak("Disable Web Search in Start", "Prevents Bing web results in Start Menu search", "Cortana & Search")
class DisableWebSearch:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                       "DisableWebSearch", 1)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                       "ConnectedSearchUseWeb", 0)
        r3 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
                       "DisableSearchBoxSuggestions", 1)
        r4 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
                       "BingSearchEnabled", 0)
        return r1 and r2 and r3 and r4

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
                        "BingSearchEnabled") == 0


@tweak("Disable Search Highlights", "Removes trending/news content from search", "Cortana & Search")
class DisableSearchHighlights:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                        "EnableDynamicContentInWSB", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                        "EnableDynamicContentInWSB") == 0


# --------------------------------------------------
# Activity & History
# --------------------------------------------------

@tweak("Disable Activity History", "Stops Windows from collecting activity history", "Activity & History")
class DisableActivityHistory:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Policies\Microsoft\Windows\System"
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "EnableActivityFeed", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "PublishUserActivities", 0)
        r3 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "UploadUserActivities", 0)
        return r1 and r2 and r3

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "PublishUserActivities") == 0


@tweak("Disable Timeline", "Disables Task View timeline feature", "Activity & History")
class DisableTimeline:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "EnableActivityFeed", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "EnableActivityFeed") == 0


@tweak("Disable Clipboard History & Sync", "Stops clipboard cloud sync and history", "Activity & History")
class DisableClipboardSync:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\System",
                       "AllowClipboardHistory", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\System",
                       "AllowCrossDeviceClipboard", 0)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "AllowCrossDeviceClipboard") == 0


@tweak("Disable App Launch Tracking", "Stops tracking which apps you launch", "Activity & History")
class DisableAppLaunchTracking:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                        "Start_TrackProgs", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                        "Start_TrackProgs") == 0


# --------------------------------------------------
# Location & Sensors
# --------------------------------------------------

@tweak("Disable Location Tracking", "Disables Windows location services", "Location & Sensors")
class DisableLocation:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                       "DisableLocation", 1)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                       "DisableWindowsLocationProvider", 1)
        r3 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                       "DisableLocationScripting", 1)
        return r1 and r2 and r3

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                        "DisableLocation") == 1


@tweak("Disable Find My Device", "Disables remote device tracking", "Location & Sensors")
class DisableFindMyDevice:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\FindMyDevice",
                        "AllowFindMyDevice", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\FindMyDevice",
                        "AllowFindMyDevice") == 0


# --------------------------------------------------
# Input & Personalization
# --------------------------------------------------

@tweak("Disable Speech Recognition Online", "Prevents sending voice data to Microsoft", "Input & Personalization")
class DisableOnlineSpeech:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\InputPersonalization",
                       "AllowInputPersonalization", 0)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\InputPersonalization",
                       "RestrictImplicitInkCollection", 1)
        r3 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\InputPersonalization",
                       "RestrictImplicitTextCollection", 1)
        r4 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\InputPersonalization\TrainedDataStore",
                       "HarvestContacts", 0)
        return r1 and r2 and r3 and r4

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\InputPersonalization",
                        "AllowInputPersonalization") == 0


@tweak("Disable Inking & Typing Personalization", "Stops collecting typing/inking patterns", "Input & Personalization")
class DisableInkingPersonalization:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\Personalization\Settings",
                       "AcceptedPrivacyPolicy", 0)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\InputPersonalization",
                       "RestrictImplicitInkCollection", 1)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\InputPersonalization",
                        "RestrictImplicitInkCollection") == 1


# --------------------------------------------------
# Camera, Microphone & Permissions
# --------------------------------------------------

@tweak("Disable Camera for Apps", "Blocks app access to camera (can re-enable per app in Settings)", "Camera, Mic & Permissions")
class DisableCamera:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessCamera", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessCamera") == 2


@tweak("Disable Microphone for Apps", "Blocks app access to microphone (can re-enable per app in Settings)", "Camera, Mic & Permissions")
class DisableMicrophone:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessMicrophone", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessMicrophone") == 2


@tweak("Disable Notifications Access", "Blocks app access to notifications", "Camera, Mic & Permissions")
class DisableNotificationsAccess:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessNotifications", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessNotifications") == 2


@tweak("Disable Account Info Access", "Blocks app access to your account info", "Camera, Mic & Permissions")
class DisableAccountInfoAccess:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessAccountInfo", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessAccountInfo") == 2


@tweak("Disable Contacts Access", "Blocks app access to contacts", "Camera, Mic & Permissions")
class DisableContactsAccess:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessContacts", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessContacts") == 2


@tweak("Disable Calendar Access", "Blocks app access to calendar", "Camera, Mic & Permissions")
class DisableCalendarAccess:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessCalendar", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessCalendar") == 2


@tweak("Disable Call History Access", "Blocks app access to call history", "Camera, Mic & Permissions")
class DisableCallHistoryAccess:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessCallHistory", 2)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                        "LetAppsAccessCallHistory") == 2


# --------------------------------------------------
# CATEGORY: Sync & Cloud
# --------------------------------------------------

@tweak("Disable Settings Sync", "Stops syncing Windows settings across devices", "Sync & Cloud")
class DisableSettingsSync:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Policies\Microsoft\Windows\SettingSync"
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "DisableSettingSync", 2)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "DisableSettingSyncUserOverride", 1)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\SettingSync",
                        "DisableSettingSync") == 2


@tweak("Disable OneDrive", "Prevents OneDrive from running at startup", "Sync & Cloud")
class DisableOneDrive:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\OneDrive",
                       "DisableFileSyncNGSC", 1)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\OneDrive",
                       "DisableFileSync", 1)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\OneDrive",
                        "DisableFileSyncNGSC") == 1


# --------------------------------------------------
# WiFi & Networking
# --------------------------------------------------

@tweak("Disable Wi-Fi Sense", "Stops automatic sharing of Wi-Fi credentials", "Wi-Fi & Networking")
class DisableWiFiSense:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config"
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "AutoConnectAllowedOEM", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowWiFiHotSpotReporting",
                       "Value", 0)
        r3 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Microsoft\PolicyManager\default\WiFi\AllowAutoConnectToWiFiSenseHotspots",
                       "Value", 0)
        return r1 and r2 and r3

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config",
                        "AutoConnectAllowedOEM") == 0


@tweak("Disable Hotspot 2.0 Networks", "Disables auto-connection to suggested hotspots", "Wi-Fi & Networking")
class DisableHotspot20:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\WlanSvc\AnqpCache",
                        "OsuRegistrationStatus", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\WlanSvc\AnqpCache",
                        "OsuRegistrationStatus") == 0


# --------------------------------------------------
# Edge & Browser
# --------------------------------------------------

@tweak("Disable Edge Telemetry", "Disables Microsoft Edge data collection", "Edge & Browser")
class DisableEdgeTelemetry:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Policies\Microsoft\Edge"
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "PersonalizationReportingEnabled", 0)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "MetricsReportingEnabled", 0)
        r3 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "SendSiteInfoToImproveServices", 0)
        r4 = _set_reg(winreg.HKEY_LOCAL_MACHINE, base, "DiagnosticData", 0)
        return r1 and r2 and r3 and r4

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Edge",
                        "MetricsReportingEnabled") == 0


@tweak("Disable Edge First Run", "Skips Edge first-run experience and data collection prompts", "Edge & Browser")
class DisableEdgeFirstRun:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Edge",
                        "HideFirstRunExperience", 1)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Edge",
                        "HideFirstRunExperience") == 1


# --------------------------------------------------
# Windows Update & Delivery
# --------------------------------------------------

@tweak("Disable Delivery Optimization P2P", "Stops Windows from sharing updates with other PCs on internet", "Windows Update")
class DisableDeliveryOptimization:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization",
                        "DODownloadMode", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization",
                        "DODownloadMode") == 0


# --------------------------------------------------
# Scheduled Tasks
# --------------------------------------------------

@tweak("Disable Telemetry Scheduled Tasks", "Disables scheduled tasks that collect/send data", "Scheduled Tasks")
class DisableTelemetryTasks:
    TASKS = [
        r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
        r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
        r"\Microsoft\Windows\Autochk\Proxy",
        r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
        r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
        r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
        r"\Microsoft\Windows\Feedback\Siuf\DmClient",
        r"\Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload",
        r"\Microsoft\Windows\Maps\MapsToastTask",
        r"\Microsoft\Windows\Maps\MapsUpdateTask",
    ]

    @staticmethod
    def apply():
        success = True
        for task in DisableTelemetryTasks.TASKS:
            if not _run(f'schtasks /Change /TN "{task}" /Disable'):
                success = False
        return success

    @staticmethod
    def check():
        r = subprocess.run(
            r'schtasks /Query /TN "\Microsoft\Windows\Customer Experience Improvement Program\Consolidator" /FO CSV',
            shell=True, capture_output=True, text=True
        )
        return "Disabled" in r.stdout


# --------------------------------------------------
# Copilot & AI (Windows 11)
# --------------------------------------------------

@tweak("Disable Windows Copilot", "Disables Windows Copilot AI assistant", "Copilot & AI")
class DisableCopilot:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
                       "TurnOffWindowsCopilot", 1)
        r2 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
                       "TurnOffWindowsCopilot", 1)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
                        "TurnOffWindowsCopilot") == 1


@tweak("Disable Recall / Snapshots", "Disables Windows Recall AI screenshot feature", "Copilot & AI")
class DisableRecall:
    @staticmethod
    def apply():
        r1 = _set_reg(winreg.HKEY_LOCAL_MACHINE,
                       r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI",
                       "DisableAIDataAnalysis", 1)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI",
                       "DisableAIDataAnalysis", 1)
        return r1 and r2

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI",
                        "DisableAIDataAnalysis") == 1


# --------------------------------------------------
# Miscellaneous
# --------------------------------------------------

@tweak("Disable Remote Assistance", "Disables remote assistance connections", "Miscellaneous")
class DisableRemoteAssistance:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SYSTEM\CurrentControlSet\Control\Remote Assistance",
                        "fAllowToGetHelp", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SYSTEM\CurrentControlSet\Control\Remote Assistance",
                        "fAllowToGetHelp") == 0


@tweak("Disable KMS Client Online Validation", "Prevents Windows activation from phoning home unnecessarily", "Miscellaneous")
class DisableKMSPhone:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows NT\CurrentVersion\Software Protection Platform",
                        "NoGenTicket", 1)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Windows NT\CurrentVersion\Software Protection Platform",
                        "NoGenTicket") == 1


@tweak("Disable Lock Screen Spotlight", "Removes Microsoft-served images and tips on lock screen", "Miscellaneous")
class DisableSpotlight:
    @staticmethod
    def apply():
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
        r1 = _set_reg(winreg.HKEY_CURRENT_USER, base, "RotatingLockScreenEnabled", 0)
        r2 = _set_reg(winreg.HKEY_CURRENT_USER, base, "RotatingLockScreenOverlayEnabled", 0)
        r3 = _set_reg(winreg.HKEY_CURRENT_USER, base,
                       "SubscribedContent-338387Enabled", 0)
        return r1 and r2 and r3

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_CURRENT_USER,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                        "RotatingLockScreenEnabled") == 0


@tweak("Disable Widgets", "Disables Windows 11 Widgets panel", "Miscellaneous")
class DisableWidgets:
    @staticmethod
    def apply():
        return _set_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Dsh",
                        "AllowNewsAndInterests", 0)

    @staticmethod
    def check():
        return _get_reg(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Policies\Microsoft\Dsh",
                        "AllowNewsAndInterests") == 0


# --------------------------------------------------
# Helpers for the GUI
# --------------------------------------------------

def get_categories():
    """Return ordered list of unique categories."""
    seen = set()
    cats = []
    for t in TWEAKS:
        if t["category"] not in seen:
            seen.add(t["category"])
            cats.append(t["category"])
    return cats


def get_tweaks_by_category(category):
    """Return all tweaks in a given category."""
    return [t for t in TWEAKS if t["category"] == category]
