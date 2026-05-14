#include "urma_failure_214.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure214> g_urma("urma_214");

bool UrmaFailure214::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_segment_get_args_list' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid param va')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure214::GetName() const
{
    return "bondp_segment_get_args_list 校验 segment 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure214::GetRootCauseDesc() const
{
    return "bondp_segment_get_args_list 在执行获取前发现调用方传入的 segment "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure214::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure214::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure214::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param va";
}

std::string UrmaFailure214::GetId() const
{
    return "urma_214";
}

} // namespace diag
