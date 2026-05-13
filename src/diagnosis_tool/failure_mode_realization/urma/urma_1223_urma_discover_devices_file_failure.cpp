#include "urma_1223_urma_discover_devices_file_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1223UrmaDiscoverDevicesFileFailure> g_urma("urma_1223");

bool Urma1223UrmaDiscoverDevicesFileFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"% open failed, errno: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1223UrmaDiscoverDevicesFileFailure::GetName() const
{
    return "urma_discover_devices 打开文件或库失败";
}

std::string Urma1223UrmaDiscoverDevicesFileFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 0";
}

RootCause Urma1223UrmaDiscoverDevicesFileFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1223UrmaDiscoverDevicesFileFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1223UrmaDiscoverDevicesFileFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：% open failed, errno: %.";
}

std::string Urma1223UrmaDiscoverDevicesFileFailure::GetId() const
{
    return "urma_1223";
}
} // namespace diag
