#include "urma_failure_651.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure651> g_urma("urma_651");

bool UrmaFailure651::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'post_recv_check_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp_recv_comp type'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure651::GetName() const
{
    return "post_recv_check_valid 校验 Jetty 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure651::GetRootCauseDesc() const
{
    return "post_recv_check_valid 在执行投递前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure651::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure651::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure651::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid bdp_recv_comp type";
}

std::string UrmaFailure651::GetId() const
{
    return "urma_651";
}

} // namespace diag
