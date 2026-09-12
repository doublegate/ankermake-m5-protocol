#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>
#include <vector>
#include <windows.h>

#include "AnkerNetBase.h"
#include "DeviceObjectBase.h"

namespace fs = std::filesystem;

using AnkerNet::AKNMT_LOG_LEVEL;
using AnkerNet::AnkerNetBase;
using AnkerNet::AnkerNetInitPara;
using AnkerNet::DeviceObjectBasePtr;
using AnkerNet::FileInfo;
using AnkerNet::SysInfo;
using AnkerNet::VrCardInfoMap;

namespace {

struct Options {
    fs::path dll_path;
    fs::path app_dir;
    fs::path data_dir;
    fs::path resources_dir;
    fs::path log_dir;
    std::string device_sn;
    std::string request_info_path;
    std::string remote_print_path;
    AKNMT_LOG_LEVEL log_level = AKNMT_LOG_LEVEL::PROTOCOL;
    bool refresh_devices = false;
    bool list_devices = false;
    bool usb_list = false;
    bool local_list = false;
    bool force_remote_print = false;
};

std::string now_string()
{
    auto now = std::chrono::system_clock::now();
    std::time_t tt = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_s(&tm, &tt);
    std::ostringstream oss;
    oss << std::put_time(&tm, "%H:%M:%S");
    return oss.str();
}

void log_line(const std::string& message)
{
    std::cout << "[" << now_string() << "] " << message << std::endl;
}

std::wstring to_wstring(const std::string& text)
{
    if (text.empty()) {
        return {};
    }
    int size = MultiByteToWideChar(CP_UTF8, 0, text.c_str(), -1, nullptr, 0);
    std::wstring out(size > 0 ? size - 1 : 0, L'\0');
    if (size > 1) {
        MultiByteToWideChar(CP_UTF8, 0, text.c_str(), -1, out.data(), size);
    }
    return out;
}

std::string wide_to_utf8(const std::wstring& text)
{
    if (text.empty()) {
        return {};
    }
    int size = WideCharToMultiByte(CP_UTF8, 0, text.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string out(size > 0 ? size - 1 : 0, '\0');
    if (size > 1) {
        WideCharToMultiByte(CP_UTF8, 0, text.c_str(), -1, out.data(), size, nullptr, nullptr);
    }
    return out;
}

std::string get_env_utf8(const wchar_t* name)
{
    DWORD size = GetEnvironmentVariableW(name, nullptr, 0);
    if (size == 0) {
        return {};
    }
    std::wstring value(size - 1, L'\0');
    GetEnvironmentVariableW(name, value.data(), size);
    return wide_to_utf8(value);
}

SysInfo collect_sys_info()
{
    SysInfo info;
    info.m_os_version = "Windows";
    HKEY key = nullptr;
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\Microsoft\\Cryptography", 0, KEY_READ | KEY_WOW64_64KEY, &key)
        == ERROR_SUCCESS) {
        wchar_t buffer[1024] = {};
        DWORD size = sizeof(buffer);
        if (RegQueryValueExW(key, L"MachineGuid", nullptr, nullptr, reinterpret_cast<LPBYTE>(buffer), &size)
            == ERROR_SUCCESS) {
            info.m_machineid = wide_to_utf8(buffer);
        }
        RegCloseKey(key);
    }
    return info;
}

bool starts_with(const std::string& value, const std::string& prefix)
{
    return value.rfind(prefix, 0) == 0;
}

std::optional<AKNMT_LOG_LEVEL> parse_log_level(std::string_view value)
{
    if (value == "MAX") {
        return AKNMT_LOG_LEVEL::MAX;
    }
    if (value == "MID") {
        return AKNMT_LOG_LEVEL::MID;
    }
    if (value == "MIN") {
        return AKNMT_LOG_LEVEL::MIN;
    }
    if (value == "PROTOCOL") {
        return AKNMT_LOG_LEVEL::PROTOCOL;
    }
    if (value == "ERRORO") {
        return AKNMT_LOG_LEVEL::ERRORO;
    }
    if (value == "SEVERE") {
        return AKNMT_LOG_LEVEL::SEVERE;
    }
    if (value == "FATAL") {
        return AKNMT_LOG_LEVEL::FATAL;
    }
    return std::nullopt;
}

void print_usage()
{
    std::cout
        << "ankernet_probe options:\n"
        << "  --dll <path>              Path to AnkerNet.dll (defaults to profile OnlineAnkerNet current DLL)\n"
        << "  --app-dir <path>          eufyMake Studio install directory\n"
        << "  --data-dir <path>         eufyMake Studio profile directory\n"
        << "  --resources-dir <path>    eufyMake Studio resources directory\n"
        << "  --device-sn <sn>          Target device serial number\n"
        << "  --refresh-devices         Trigger AsyRefreshDeviceList()\n"
        << "  --list-devices            Print discovered devices\n"
        << "  --usb-list                Request USB file list and dump getDeviceFileList()\n"
        << "  --local-list              Request onboard file list and dump getDeviceFileList()\n"
        << "  --request-info <path>     Request GCode info for a stored file path\n"
        << "  --remote-print <path>     Invoke SetRemotePrintData({}, path)\n"
        << "  --force                   Required together with --remote-print\n"
        << "  --log-level <LEVEL>       MAX|MID|MIN|PROTOCOL|ERRORO|SEVERE|FATAL\n";
}

bool parse_args(int argc, char** argv, Options& options)
{
    auto next_value = [&](int& index) -> const char* {
        if (index + 1 >= argc) {
            return nullptr;
        }
        ++index;
        return argv[index];
    };

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--dll") {
            if (const char* value = next_value(i)) {
                options.dll_path = value;
            } else {
                return false;
            }
        } else if (arg == "--app-dir") {
            if (const char* value = next_value(i)) {
                options.app_dir = value;
            } else {
                return false;
            }
        } else if (arg == "--data-dir") {
            if (const char* value = next_value(i)) {
                options.data_dir = value;
            } else {
                return false;
            }
        } else if (arg == "--resources-dir") {
            if (const char* value = next_value(i)) {
                options.resources_dir = value;
            } else {
                return false;
            }
        } else if (arg == "--device-sn") {
            if (const char* value = next_value(i)) {
                options.device_sn = value;
            } else {
                return false;
            }
        } else if (arg == "--request-info") {
            if (const char* value = next_value(i)) {
                options.request_info_path = value;
            } else {
                return false;
            }
        } else if (arg == "--remote-print") {
            if (const char* value = next_value(i)) {
                options.remote_print_path = value;
            } else {
                return false;
            }
        } else if (arg == "--log-level") {
            if (const char* value = next_value(i)) {
                auto parsed = parse_log_level(value);
                if (!parsed.has_value()) {
                    return false;
                }
                options.log_level = *parsed;
            } else {
                return false;
            }
        } else if (arg == "--refresh-devices") {
            options.refresh_devices = true;
        } else if (arg == "--list-devices") {
            options.list_devices = true;
        } else if (arg == "--usb-list") {
            options.usb_list = true;
        } else if (arg == "--local-list") {
            options.local_list = true;
        } else if (arg == "--force") {
            options.force_remote_print = true;
        } else if (arg == "--help" || arg == "-h") {
            print_usage();
            std::exit(0);
        } else {
            return false;
        }
    }
    return true;
}

fs::path find_default_dll(const fs::path& data_dir)
{
    fs::path current_dir = data_dir / "OnlineAnkerNet" / "Current";
    if (!fs::exists(current_dir)) {
        return {};
    }
    for (const auto& entry : fs::directory_iterator(current_dir)) {
        if (!entry.is_regular_file()) {
            continue;
        }
        auto name = entry.path().filename().string();
        if (starts_with(name, "AnkerNet_") && entry.path().extension() == ".dll") {
            return entry.path();
        }
    }
    return {};
}

void dump_devices(AnkerNetBase* net)
{
    auto devices = net->GetDeviceList();
    std::cout << "Devices: " << devices.size() << std::endl;
    for (const auto& dev : devices) {
        if (!dev) {
            continue;
        }
        std::cout
            << "  sn=" << dev->GetSn()
            << " name=" << dev->GetStationName()
            << " online=" << dev->GetOnline()
            << " busy=" << dev->IsBusy()
            << " gui_status=" << dev->getGuiDeviceStatus()
            << std::endl;
    }
}

DeviceObjectBasePtr resolve_device(AnkerNetBase* net, const std::string& sn)
{
    if (!sn.empty()) {
        return net->getDeviceObjectFromSn(sn);
    }
    auto devices = net->GetDeviceList();
    if (devices.empty()) {
        return nullptr;
    }
    return devices.front();
}

void dump_files(DeviceObjectBasePtr dev)
{
    auto files = dev->getDeviceFileList();
    std::cout << "Files: " << files.size() << std::endl;
    for (const FileInfo& file : files) {
        std::cout << "  " << file.path << " (" << file.name << ", ts=" << file.timestamp << ")" << std::endl;
    }
}

} // namespace

int main(int argc, char** argv)
{
    Options options;
    if (!parse_args(argc, argv, options)) {
        print_usage();
        return 2;
    }

    std::string local_appdata = get_env_utf8(L"LOCALAPPDATA");
    std::string roaming_appdata = get_env_utf8(L"APPDATA");

    if (options.app_dir.empty()) {
        options.app_dir = fs::path(local_appdata) / "eufyMake Studio";
    }
    if (options.data_dir.empty()) {
        options.data_dir = fs::path(roaming_appdata) / "eufyMake Studio Profile";
    }
    if (options.resources_dir.empty()) {
        options.resources_dir = options.app_dir / "resources";
    }
    if (options.log_dir.empty()) {
        options.log_dir = options.data_dir / "logs";
    }
    if (options.dll_path.empty()) {
        options.dll_path = find_default_dll(options.data_dir);
    }

    if (options.dll_path.empty() || !fs::exists(options.dll_path)) {
        std::cerr << "Could not find AnkerNet.dll. Use --dll <path>." << std::endl;
        return 3;
    }

    fs::create_directories(options.log_dir);

    log_line("Loading DLL: " + options.dll_path.string());
    SetDllDirectoryW(options.app_dir.wstring().c_str());
    HMODULE module = LoadLibraryW(options.dll_path.wstring().c_str());
    if (!module) {
        std::cerr << "LoadLibraryW failed: " << GetLastError() << std::endl;
        return 4;
    }

    auto get_ankernet = reinterpret_cast<GetAnkerNet_T>(GetProcAddress(module, "GetAnkerNet"));
    if (!get_ankernet) {
        std::cerr << "GetProcAddress(GetAnkerNet) failed" << std::endl;
        return 5;
    }

    AnkerNetBase* net = get_ankernet();
    if (!net) {
        std::cerr << "GetAnkerNet returned nullptr" << std::endl;
        return 6;
    }

    LogOutputCallBackFunc log_cb = [](unsigned int level,
                                      const std::string strLogMsg,
                                      const std::string strFileName,
                                      const std::string strFuncName,
                                      const unsigned int lineNumber) {
        std::cout
            << "[ankernet-log] level=" << level
            << " file=" << strFileName
            << " func=" << strFuncName
            << ":" << lineNumber
            << " :: " << strLogMsg
            << std::endl;
    };

    SysInfo sys_info = collect_sys_info();
    AnkerNetInitPara para;
    para.Model_type = "PC";
    para.App_name = "AnkerMake Studio";
    para.App_version_V = "V1.5.26";
    para.App_version = "1.5.26";
    para.Version_code = 105026;
    para.Country = "US";
    para.Language = "en";
    para.Openudid = sys_info.m_machineid;
    para.Os_version = sys_info.m_os_version;
    para.Os_type = "Windows";
    para.Content_Type = "Content-Type:application/json;charset=UTF-8";
    para.exeDir = (options.app_dir / "eufymake studio.exe").string();
    para.dataDir = options.data_dir.string();
    para.resourcesDir = options.resources_dir.string();
    para.certDir = options.app_dir.string();
    para.logDir = options.log_dir.string();
    para.aknmtLogLevel = options.log_level;
    para.sysInfo = sys_info;

    net->setLogOutputCallBack(log_cb);
    log_line("Calling Init(...)");
    bool init_ok = net->Init(para);
    std::cout << "Init returned: " << init_ok << std::endl;
    std::cout << "IsInit: " << net->IsInit() << std::endl;
    net->ProcessWebLoginFinish();
    std::cout << "UserId: " << net->GetUserId() << std::endl;
    std::cout << "NickName: " << net->GetNickName() << std::endl;

    if (options.refresh_devices) {
        log_line("Calling AsyRefreshDeviceList()");
        net->AsyRefreshDeviceList();
        std::this_thread::sleep_for(std::chrono::seconds(5));
    }

    if (options.list_devices || options.device_sn.empty()) {
        dump_devices(net);
    }

    DeviceObjectBasePtr device = resolve_device(net, options.device_sn);
    if (!device) {
        std::cerr << "No device resolved. Use --refresh-devices or provide --device-sn." << std::endl;
        return 7;
    }

    log_line("Resolved device sn=" + device->GetSn() + " name=" + device->GetStationName());

    if (options.local_list) {
        log_line("Calling getDeviceLocalFileLists()");
        device->getDeviceLocalFileLists();
        std::this_thread::sleep_for(std::chrono::seconds(3));
        dump_files(device);
    }

    if (options.usb_list) {
        log_line("Calling getDeviceUsbFileLists()");
        device->getDeviceUsbFileLists();
        std::this_thread::sleep_for(std::chrono::seconds(3));
        dump_files(device);
    }

    if (!options.request_info_path.empty()) {
        log_line("Calling setRequestGCodeInfo(" + options.request_info_path + ")");
        device->setRequestGCodeInfo(options.request_info_path);
        std::this_thread::sleep_for(std::chrono::seconds(5));
        auto info = device->GetGcodeInfo();
        std::cout
            << "GCodeInfo file_status=" << info.file_status
            << " fileName=" << info.fileName
            << " leftTime=" << info.leftTime
            << " filamentUsed=" << info.filamentUsed
            << " filamentUnit=" << info.filamentUnit
            << std::endl;
    }

    if (!options.remote_print_path.empty()) {
        if (!options.force_remote_print) {
            std::cerr << "--remote-print requires --force" << std::endl;
            return 8;
        }
        log_line("Calling SetRemotePrintData({}, " + options.remote_print_path + ")");
        VrCardInfoMap vr_card_info_map;
        device->SetRemotePrintData(vr_card_info_map, options.remote_print_path);
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }

    log_line("Done");
    return 0;
}
