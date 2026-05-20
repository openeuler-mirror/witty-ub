#include "urma_failure_079.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure079> g_urma("urma_079");

bool UrmaFailure079::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_deactive_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure079::GetName() const
{
    return "urma_cmd_deactive_jetty 校验 context 无效导致激活流程拒绝继续执行";
}

std::string UrmaFailure079::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_jetty 在执行激活前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure079::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure079::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure079::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure079::GetId() const
{
    return "urma_079";
}

} // namespace diag
