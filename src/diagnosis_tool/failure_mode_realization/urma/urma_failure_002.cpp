#include "urma_failure_002.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure002> g_urma("urma_002");

bool UrmaFailure002::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_provider_bond_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Provider Bond register ops failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure002::GetName() const
{
    return "urma_provider_bond_init 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure002::GetRootCauseDesc() const
{
    return "urma_provider_bond_init 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure002::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure002::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Provider Bond register ops failed";
}

std::string UrmaFailure002::GetId() const
{
    return "urma_002";
}

} // namespace diag
