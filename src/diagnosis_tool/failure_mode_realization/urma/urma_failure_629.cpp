#include "urma_failure_629.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure629> g_urma("urma_629");

bool UrmaFailure629::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'schedule_send' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid wr->tjetty: NULL')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure629::GetName() const
{
    return "schedule_send 校验 目标 Jetty 无效导致发送流程拒绝继续执行";
}

std::string UrmaFailure629::GetRootCauseDesc() const
{
    return "schedule_send 在执行发送前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure629::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure629::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure629::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid wr->tjetty: NULL";
}

std::string UrmaFailure629::GetId() const
{
    return "urma_629";
}

} // namespace diag
