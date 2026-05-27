#include "urma_failure_666.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure666> g_urma("urma_666");

bool UrmaFailure666::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure666::GetName() const
{
    return "URMA context、provider操作表、JFR对象、provider未提供free_jfr操作实现无效导致释放JFR失败";
}

std::string UrmaFailure666::GetRootCauseDesc() const
{
    return "函数用于释放JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象、provider未提供free_"
           "jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure666::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure666::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure666::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jfr，Invalid parameter.";
}

std::string UrmaFailure666::GetId() const
{
    return "urma_666";
}

} // namespace diag
