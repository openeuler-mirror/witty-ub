#include "urma_failure_627.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure627> g_urma("urma_627");

bool UrmaFailure627::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'comp_post_recv' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid post jfr wr type')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure627::GetName() const
{
    return "comp_post_recv 校验 context 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure627::GetRootCauseDesc() const
{
    return "comp_post_recv 在执行投递前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure627::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure627::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure627::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid post jfr wr type";
}

std::string UrmaFailure627::GetId() const
{
    return "urma_627";
}

} // namespace diag
