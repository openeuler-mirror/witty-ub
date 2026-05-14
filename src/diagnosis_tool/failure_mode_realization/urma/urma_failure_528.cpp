#include "urma_failure_528.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure528> g_urma("urma_528");

bool UrmaFailure528::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_get_jetty_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure528::GetName() const
{
    return "urma_get_jetty_opt 校验 Jetty 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure528::GetRootCauseDesc() const
{
    return "urma_get_jetty_opt 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure528::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure528::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure528::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure528::GetId() const
{
    return "urma_528";
}

} // namespace diag
