#include "urma_failure_882.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure882> g_urma("urma_882");

bool UrmaFailure882::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_modify_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure882::GetName() const
{
    return "urma_modify_jetty 校验 Jetty 无效导致修改流程拒绝继续执行";
}

std::string UrmaFailure882::GetRootCauseDesc() const
{
    return "urma_modify_jetty 在执行修改前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure882::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure882::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure882::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure882::GetId() const
{
    return "urma_882";
}

} // namespace diag
