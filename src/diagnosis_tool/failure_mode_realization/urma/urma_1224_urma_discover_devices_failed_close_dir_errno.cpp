#include "urma_1224_urma_discover_devices_failed_close_dir_errno.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1224UrmaDiscoverDevicesFailedCloseDirErrno> g_urma("urma_1224");

bool Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed close dir: %, errno: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::GetName() const
{
    return "urma_discover_devices Failed close dir: %, errno: %.";
}

std::string Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `closedir(class_dir) < 0`";
}

RootCause Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed close dir: %, errno: %.";
}

std::string Urma1224UrmaDiscoverDevicesFailedCloseDirErrno::GetId() const
{
    return "urma_1224";
}
} // namespace diag
