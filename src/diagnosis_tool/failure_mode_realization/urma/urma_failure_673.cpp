#include "urma_failure_673.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure673> g_urma("urma_673");

bool UrmaFailure673::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_ack_notify' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure673::GetName() const
{
    return "urma_ack_notify 校验 context 无效导致确认流程拒绝继续执行";
}

std::string UrmaFailure673::GetRootCauseDesc() const
{
    return "urma_ack_notify 在执行确认前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure673::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure673::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure673::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure673::GetId() const
{
    return "urma_673";
}

} // namespace diag
