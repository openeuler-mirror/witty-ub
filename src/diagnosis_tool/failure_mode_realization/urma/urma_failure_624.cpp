#include "urma_failure_624.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure624> g_urma("urma_624");

bool UrmaFailure624::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'failed to get invalid jetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure624::GetName() const
{
    return "bondp_get_async_event 校验 Jetty 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure624::GetRootCauseDesc() const
{
    return "bondp_get_async_event 在执行获取前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure624::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure624::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure624::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：failed to get invalid jetty";
}

std::string UrmaFailure624::GetId() const
{
    return "urma_624";
}

} // namespace diag
