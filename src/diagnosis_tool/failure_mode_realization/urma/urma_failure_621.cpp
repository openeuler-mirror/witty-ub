#include "urma_failure_621.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure621> g_urma("urma_621");

bool UrmaFailure621::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure621::GetName() const
{
    return "bondp_get_async_event 校验 context 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure621::GetRootCauseDesc() const
{
    return "bondp_get_async_event 在执行获取前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure621::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure621::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure621::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure621::GetId() const
{
    return "urma_621";
}

} // namespace diag
