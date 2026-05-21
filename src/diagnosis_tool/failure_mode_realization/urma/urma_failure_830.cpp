#include "urma_failure_830.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure830> g_urma("urma_830");

bool UrmaFailure830::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_open_drivers' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'snprintf_s' | "
        "grep -F 'failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure830::GetName() const
{
    return "urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure830::GetRootCauseDesc() const
{
    return "urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure830::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure830::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure830::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：snprintf_s failed";
}

std::string UrmaFailure830::GetId() const
{
    return "urma_830";
}

} // namespace diag
