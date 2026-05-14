#include "urma_failure_682.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure682> g_urma("urma_682");

bool UrmaFailure682::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_recv' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'There are invalid parameters')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure682::GetName() const
{
    return "urma_recv 校验 JFR 无效导致接收流程拒绝继续执行";
}

std::string UrmaFailure682::GetRootCauseDesc() const
{
    return "urma_recv 在执行接收前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure682::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure682::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure682::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：There are invalid parameters";
}

std::string UrmaFailure682::GetId() const
{
    return "urma_682";
}

} // namespace diag
