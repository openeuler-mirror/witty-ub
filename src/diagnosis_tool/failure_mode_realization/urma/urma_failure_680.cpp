#include "urma_failure_680.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure680> g_urma("urma_680");

bool UrmaFailure680::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_send' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure680::GetName() const
{
    return "urma_send 校验 目标 segment 无效导致发送流程拒绝继续执行";
}

std::string UrmaFailure680::GetRootCauseDesc() const
{
    return "urma_send 在执行发送前发现调用方传入的 目标 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure680::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure680::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure680::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure680::GetId() const
{
    return "urma_680";
}

} // namespace diag
