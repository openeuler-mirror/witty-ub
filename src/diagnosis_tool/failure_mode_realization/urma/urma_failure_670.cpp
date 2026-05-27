#include "urma_failure_670.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure670> g_urma("urma_670");

bool UrmaFailure670::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure670::GetName() const
{
    return "URMA context、provider操作表、JFR对象、provider未提供delete_jfr操作实现无效导致删除JFR失败";
}

std::string UrmaFailure670::GetRootCauseDesc() const
{
    return "函数用于删除JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象、provider未提供delete_"
           "jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure670::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure670::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure670::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfr，Invalid parameter.";
}

std::string UrmaFailure670::GetId() const
{
    return "urma_670";
}

} // namespace diag
