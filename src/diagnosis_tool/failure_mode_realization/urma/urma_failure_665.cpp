#include "urma_failure_665.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure665> g_urma("urma_665");

bool UrmaFailure665::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_wait_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure665::GetName() const
{
    return "urma_cmd_wait_notify 校验 fd 无效导致等待流程拒绝继续执行";
}

std::string UrmaFailure665::GetRootCauseDesc() const
{
    return "urma_cmd_wait_notify 在执行等待前发现调用方传入的 fd 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure665::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure665::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure665::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure665::GetId() const
{
    return "urma_665";
}

} // namespace diag
