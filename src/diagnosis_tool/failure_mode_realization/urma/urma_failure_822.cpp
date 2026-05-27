#include "urma_failure_822.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure822> g_urma("urma_822");

bool UrmaFailure822::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure822::GetName() const
{
    return "URMA context、provider操作表、JFR对象、provider未提供deactive_jfr操作实现无效导致去激活JFR失败";
}

std::string UrmaFailure822::GetRootCauseDesc() const
{
    return "函数用于去激活JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象、provider未提供deactive_"
           "jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure822::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure822::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure822::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfr，Invalid parameter.";
}

std::string UrmaFailure822::GetId() const
{
    return "urma_822";
}

} // namespace diag
