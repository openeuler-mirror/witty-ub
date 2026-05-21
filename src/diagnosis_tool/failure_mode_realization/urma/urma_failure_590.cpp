#include "urma_failure_590.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure590> g_urma("urma_590");

bool UrmaFailure590::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_unimport_jetty_async' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure590::GetName() const
{
    return "urma_cmd_unimport_jetty_async 校验 目标 Jetty 无效导致导入流程拒绝继续执行";
}

std::string UrmaFailure590::GetRootCauseDesc() const
{
    return "urma_cmd_unimport_jetty_async 在执行导入前发现调用方传入的 目标 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure590::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure590::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure590::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure590::GetId() const
{
    return "urma_590";
}

} // namespace diag
