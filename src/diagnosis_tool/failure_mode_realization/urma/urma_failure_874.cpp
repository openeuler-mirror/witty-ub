#include "urma_failure_874.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure874> g_urma("urma_874");

bool UrmaFailure874::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_check_opt_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure874::GetName() const
{
    return "urma_check_opt_valid 校验 映射表 无效导致校验流程拒绝继续执行";
}

std::string UrmaFailure874::GetRootCauseDesc() const
{
    return "urma_check_opt_valid 在执行校验前发现调用方传入的 映射表 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure874::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure874::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure874::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：invalid opt len";
}

std::string UrmaFailure874::GetId() const
{
    return "urma_874";
}

} // namespace diag
