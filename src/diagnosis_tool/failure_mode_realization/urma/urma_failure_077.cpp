#include "urma_failure_077.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure077> g_urma("urma_077");

bool UrmaFailure077::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_active_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid flag'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure077::GetName() const
{
    return "urma_cmd_active_jetty 校验 Jetty 无效导致激活流程拒绝继续执行";
}

std::string UrmaFailure077::GetRootCauseDesc() const
{
    return "urma_cmd_active_jetty 在执行激活前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure077::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure077::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure077::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid flag";
}

std::string UrmaFailure077::GetId() const
{
    return "urma_077";
}

} // namespace diag
