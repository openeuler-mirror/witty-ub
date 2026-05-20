#include "urma_failure_683.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure683> g_urma("urma_683");

bool UrmaFailure683::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_poll_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure683::GetName() const
{
    return "urma_poll_jfc 校验 JFC 无效导致轮询流程拒绝继续执行";
}

std::string UrmaFailure683::GetRootCauseDesc() const
{
    return "urma_poll_jfc 在执行轮询前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure683::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure683::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure683::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure683::GetId() const
{
    return "urma_683";
}

} // namespace diag
