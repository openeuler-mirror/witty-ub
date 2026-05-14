#include "urma_failure_413.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure413> g_urma("urma_413");

bool UrmaFailure413::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_set_jfr_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure413::GetName() const
{
    return "urma_set_jfr_opt 校验 context 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure413::GetRootCauseDesc() const
{
    return "urma_set_jfr_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure413::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure413::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure413::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure413::GetId() const
{
    return "urma_413";
}

} // namespace diag
