#include "urma_failure_690.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure690> g_urma("urma_690");

bool UrmaFailure690::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_post_jetty_send_wr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure690::GetName() const
{
    return "urma_post_jetty_send_wr 校验 Jetty 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure690::GetRootCauseDesc() const
{
    return "urma_post_jetty_send_wr 在执行投递前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure690::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure690::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure690::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure690::GetId() const
{
    return "urma_690";
}

} // namespace diag
