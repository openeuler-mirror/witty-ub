#include "urma_failure_844.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure844> g_urma("urma_844");

bool UrmaFailure844::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_user_ctl' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid len')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure844::GetName() const
{
    return "bondp_user_ctl 校验 context 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure844::GetRootCauseDesc() const
{
    return "bondp_user_ctl 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure844::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure844::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure844::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid len";
}

std::string UrmaFailure844::GetId() const
{
    return "urma_844";
}

} // namespace diag
