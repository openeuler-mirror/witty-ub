#include "urma_failure_618.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure618> g_urma("urma_618");

bool UrmaFailure618::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_wait_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid param')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure618::GetName() const
{
    return "bondp_wait_jfc 校验 JFCE 无效导致等待流程拒绝继续执行";
}

std::string UrmaFailure618::GetRootCauseDesc() const
{
    return "bondp_wait_jfc 在执行等待前发现调用方传入的 JFCE 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure618::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure618::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure618::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param";
}

std::string UrmaFailure618::GetId() const
{
    return "urma_618";
}

} // namespace diag
