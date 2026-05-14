#include "urma_failure_614.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure614> g_urma("urma_614");

bool UrmaFailure614::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_register_sysfs_dev' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Register device failed. Failed to match driver for device')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure614::GetName() const
{
    return "urma_register_sysfs_dev 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure614::GetRootCauseDesc() const
{
    return "urma_register_sysfs_dev 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure614::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure614::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure614::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Register device failed. Failed to match driver for device";
}

std::string UrmaFailure614::GetId() const
{
    return "urma_614";
}

} // namespace diag
