#include "urma_failure_825.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure825> g_urma("urma_825");

bool UrmaFailure825::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure825::GetName() const
{
    return "URMA context、provider操作表、provider未提供create_jfce操作实现无效导致去激活JFR失败";
}

std::string UrmaFailure825::GetRootCauseDesc() const
{
    return "函数用于去激活JFR，调用方传入的URMA "
           "context、provider操作表、provider未提供create_jfce操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure825::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure825::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure825::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfr，Invalid parameter.";
}

std::string UrmaFailure825::GetId() const
{
    return "urma_825";
}

} // namespace diag
