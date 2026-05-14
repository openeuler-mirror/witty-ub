#include "urma_failure_679.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure679> g_urma("urma_679");

bool UrmaFailure679::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_send' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure679::GetName() const
{
    return "urma_send 校验 JFS 无效导致发送流程拒绝继续执行";
}

std::string UrmaFailure679::GetRootCauseDesc() const
{
    return "urma_send 在执行发送前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure679::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure679::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure679::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure679::GetId() const
{
    return "urma_679";
}

} // namespace diag
