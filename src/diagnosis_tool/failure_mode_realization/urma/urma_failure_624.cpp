#include "urma_failure_624.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure624> g_urma("urma_624");

bool UrmaFailure624::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfr_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure624::GetName() const
{
    return "URMA context、JFR对象无效导致删除JFR失败";
}

std::string UrmaFailure624::GetRootCauseDesc() const
{
    return "函数用于删除JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
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
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfr_batch，Invalid parameter.";
}

std::string UrmaFailure624::GetId() const
{
    return "urma_624";
}

} // namespace diag
