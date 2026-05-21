#include "urma_failure_655.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure655> g_urma("urma_655");

bool UrmaFailure655::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'handle_send' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp_comp type'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure655::GetName() const
{
    return "handle_send 校验 context 无效导致发送流程拒绝继续执行";
}

std::string UrmaFailure655::GetRootCauseDesc() const
{
    return "handle_send 在执行发送前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure655::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure655::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure655::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid bdp_comp type";
}

std::string UrmaFailure655::GetId() const
{
    return "urma_655";
}

} // namespace diag
