#include "urma_failure_759.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure759> g_urma("urma_759");

bool UrmaFailure759::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure759::GetName() const
{
    return "URMA context、JFR对象无效导致设置JFR失败";
}

std::string UrmaFailure759::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure759::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure759::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure759::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure759::GetId() const
{
    return "urma_759";
}

} // namespace diag
