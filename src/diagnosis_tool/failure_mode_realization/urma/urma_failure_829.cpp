#include "urma_failure_829.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure829> g_urma("urma_829");

bool UrmaFailure829::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_open_drivers' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to open liburma dir')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure829::GetName() const
{
    return "urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure829::GetRootCauseDesc() const
{
    return "urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure829::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure829::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure829::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to open liburma dir";
}

std::string UrmaFailure829::GetId() const
{
    return "urma_829";
}

} // namespace diag
