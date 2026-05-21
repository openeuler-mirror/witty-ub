#include "urma_failure_656.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure656> g_urma("urma_656");

bool UrmaFailure656::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'handle_recv' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp_comp type'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure656::GetName() const
{
    return "handle_recv 校验 context 无效导致接收流程拒绝继续执行";
}

std::string UrmaFailure656::GetRootCauseDesc() const
{
    return "handle_recv 在执行接收前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure656::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure656::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure656::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid bdp_comp type";
}

std::string UrmaFailure656::GetId() const
{
    return "urma_656";
}

} // namespace diag
