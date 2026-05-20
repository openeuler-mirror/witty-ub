#include "urma_failure_489.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure489> g_urma("urma_489");

bool UrmaFailure489::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid option name'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure489::GetName() const
{
    return "urma_set_context_opt 校验 context 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure489::GetRootCauseDesc() const
{
    return "urma_set_context_opt 在执行设置前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure489::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure489::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure489::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid option name";
}

std::string UrmaFailure489::GetId() const
{
    return "urma_489";
}

} // namespace diag
