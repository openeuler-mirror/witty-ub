#include "urma_failure_691.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure691> g_urma("urma_691");

bool UrmaFailure691::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_post_jetty_recv_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure691::GetName() const
{
    return "urma_post_jetty_recv_wr 校验 Jetty 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure691::GetRootCauseDesc() const
{
    return "urma_post_jetty_recv_wr 在执行投递前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure691::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure691::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure691::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure691::GetId() const
{
    return "urma_691";
}

} // namespace diag
