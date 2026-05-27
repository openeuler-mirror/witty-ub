#include "urma_failure_357.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure357> g_urma("urma_357");

bool UrmaFailure357::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure357::GetName() const
{
    return "URMA context、Segment对象无效导致分配Token失败";
}

std::string UrmaFailure357::GetRootCauseDesc() const
{
    return "函数用于分配Token，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure357::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure357::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure357::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_alloc_token_id，Invalid parameter";
}

std::string UrmaFailure357::GetId() const
{
    return "urma_357";
}

} // namespace diag
