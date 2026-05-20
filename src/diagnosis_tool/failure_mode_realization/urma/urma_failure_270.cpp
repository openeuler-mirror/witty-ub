#include "urma_failure_270.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure270> g_urma("urma_270");

bool UrmaFailure270::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid segment address for bondp seg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure270::GetName() const
{
    return "bondp_create_pseg 校验 segment 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure270::GetRootCauseDesc() const
{
    return "bondp_create_pseg 在执行创建前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure270::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure270::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure270::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid segment address for bondp seg";
}

std::string UrmaFailure270::GetId() const
{
    return "urma_270";
}

} // namespace diag
