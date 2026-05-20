#include "urma_failure_444.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure444> g_urma("urma_444");

bool UrmaFailure444::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure444::GetName() const
{
    return "urma_set_jetty_opt 校验 Jetty 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure444::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt 在执行设置前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure444::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure444::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure444::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：invalid opt id or opt len";
}

std::string UrmaFailure444::GetId() const
{
    return "urma_444";
}

} // namespace diag
