#include "urma_failure_255.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure255> g_urma("urma_255");

bool UrmaFailure255::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'init_general_slave_devices' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to get slave device info')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure255::GetName() const
{
    return "init_general_slave_devices 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure255::GetRootCauseDesc() const
{
    return "init_general_slave_devices 在初始化或注册设备时未能打开 provider "
           "动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider "
           "操作集。";
}

RootCause UrmaFailure255::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure255::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure255::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get slave device info";
}

std::string UrmaFailure255::GetId() const
{
    return "urma_255";
}

} // namespace diag
