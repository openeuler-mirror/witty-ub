#include "urma_failure_821.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure821> g_urma("urma_821");

bool UrmaFailure821::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_check_jetty_cfg_with_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid token with unshared jfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure821::GetName() const
{
    return "urma_check_jetty_cfg_with_jetty_grp 校验 Jetty 无效导致校验流程拒绝继续执行";
}

std::string UrmaFailure821::GetRootCauseDesc() const
{
    return "urma_check_jetty_cfg_with_jetty_grp 在执行校验前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure821::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure821::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure821::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid token with unshared jfr";
}

std::string UrmaFailure821::GetId() const
{
    return "urma_821";
}

} // namespace diag
