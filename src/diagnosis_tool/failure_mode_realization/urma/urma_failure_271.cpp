#include "urma_failure_271.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure271> g_urma("urma_271");

bool UrmaFailure271::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to register pseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure271::GetName() const
{
    return "bondp_create_pseg 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure271::GetRootCauseDesc() const
{
    return "bondp_create_pseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure271::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure271::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure271::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to register pseg";
}

std::string UrmaFailure271::GetId() const
{
    return "urma_271";
}

} // namespace diag
