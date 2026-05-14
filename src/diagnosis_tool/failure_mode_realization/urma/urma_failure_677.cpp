#include "urma_failure_677.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure677> g_urma("urma_677");

bool UrmaFailure677::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_ack_async_event' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter with ops nullptr')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure677::GetName() const
{
    return "urma_ack_async_event 校验 异步事件 无效导致确认流程拒绝继续执行";
}

std::string UrmaFailure677::GetRootCauseDesc() const
{
    return "urma_ack_async_event 在执行确认前发现调用方传入的 异步事件 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure677::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure677::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure677::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter with ops nullptr";
}

std::string UrmaFailure677::GetId() const
{
    return "urma_677";
}

} // namespace diag
